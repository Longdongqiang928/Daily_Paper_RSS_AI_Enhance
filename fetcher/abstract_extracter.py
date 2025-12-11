"""Abstract Extractor Module

Provides a unified interface for extracting paper abstracts using multiple methods:
1. Nature/Springer API (for Nature series publications)
2. crawl4ai web crawler (for other sources)
3. Tavily API (fallback when other methods fail)

Usage:
    from fetcher.abstract_extracter import AbstractExtractor
    
    extractor = AbstractExtractor()
    papers_with_abstracts = extractor.extract_abstracts(papers)
"""

import os
import sys
from typing import List, Dict, Optional, Tuple
import requests
import xml.etree.ElementTree as ET
from tavily import TavilyClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger
from config import config

logger = get_logger(__name__)


class AbstractExtractor:
    """
    Unified abstract extraction with fallback chain:
    1. Nature/Springer API (for Nature series publications)
    2. Tavily API (fallback when other methods fail)
    """
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        """
        Initialize the AbstractExtractor.
        
        Args:
            tavily_api_key: Tavily API key. If not provided, will try to get from TAVILY_API_KEY env var.
        """
        self.tavily_api_key = tavily_api_key or config.TAVILY_API_KEY
        self.tavily_client = None
        if self.tavily_api_key:
            self.tavily_client = TavilyClient(self.tavily_api_key)
            logger.info("Tavily client initialized")
        else:
            logger.warning("Tavily API key not provided. Tavily fallback will not be available.")
    
    def extract_abstracts(self, papers: List[Dict], source: str = "nature") -> List[Dict]:
        """
        Extract abstracts for a list of papers using the fallback chain.
        
        Args:
            papers: List of paper dictionaries with 'id' (DOI) and 'abs' (URL) fields
            source: Source name (e.g., 'nature', 'science', 'optica')
            
        Returns:
            List of paper dictionaries with filled 'summary' fields
        """
        logger.info(f"[{source}] Starting abstract extraction for {len(papers)} papers")
        
        # Step 1: Try Nature API for all papers (batch processing)
        if source == "nature":
            papers_with_abs, papers_without_abs = self._try_nature_api(papers, source)
        else:
            papers_with_abs, papers_without_abs = [], papers
        
        if not papers_without_abs:
            logger.info(f"[{source}] All {len(papers_with_abs)} papers have abstracts from Nature API")
            return papers_with_abs
        
        logger.info(f"[{source}] {len(papers_without_abs)} papers still need abstracts after Nature API")
        
        # Step 2: Try Tavily for remaining papers with up to 3 retries
        max_retries = 3
        remaining_papers = papers_without_abs
        
        for retry in range(1, max_retries + 1):
            if not remaining_papers:
                break
            
            logger.info(f"[{source}] Tavily attempt {retry}/{max_retries} for {len(remaining_papers)} papers")
            tavily_papers, failed_papers = self._try_tavily(remaining_papers, source)
            papers_with_abs.extend(tavily_papers)
            
            if not failed_papers:
                logger.info(f"[{source}] All papers have abstracts after Tavily attempt {retry}")
                break
            
            remaining_papers = failed_papers
            
            if retry < max_retries:
                logger.info(f"[{source}] {len(remaining_papers)} papers still need abstracts, will retry...")
        
        if remaining_papers:
            logger.warning(f"[{source}] {len(remaining_papers)} papers failed to get abstracts after {max_retries} Tavily attempts")
            # Include failed papers with empty summaries
            papers_with_abs.extend(remaining_papers)
        
        logger.info(f"[{source}] Abstract extraction complete: {len([p for p in papers_with_abs if p.get('summary')])} papers with abstracts")
        return papers_with_abs
    
    def _try_nature_api(self, papers: List[Dict], source: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Try to fetch abstracts using Nature/Springer API.
        
        Returns:
            Tuple of (papers with abstracts, papers without abstracts)
        """
        papers_with_abs = []
        papers_without_abs = []
        
        # Extract DOIs for batch processing
        doi_to_paper = {}
        dois_to_fetch = []
        
        for paper in papers:
            # Skip papers that already have abstracts
            if paper.get('summary'):
                papers_with_abs.append(paper)
                continue
            
            # Extract DOI from paper
            doi = paper.get('id')
            if not doi and 'doi.org/' in paper.get('abs', ''):
                doi = paper['abs'].split('doi.org/')[-1]
            
            if doi:
                dois_to_fetch.append(doi)
                doi_to_paper[doi] = paper
            else:
                papers_without_abs.append(paper)
        
        if not dois_to_fetch:
            return papers_with_abs, papers_without_abs
        
        logger.info(f"[{source}] Fetching abstracts for {len(dois_to_fetch)} DOIs via Nature API")
        
        # Fetch abstracts in batches
        batch_size = 20
        fetched_dois = set()
        
        for i in range(0, len(dois_to_fetch), batch_size):
            batch = dois_to_fetch[i:i + batch_size]
            logger.info(f"[{source}] Fetching batch {i//batch_size + 1} ({len(batch)} DOIs)")
            
            try:
                fetched_papers = self._fetch_nature_api_batch(batch, source)
                for fp in fetched_papers:
                    doi = fp.get('id')
                    if doi in doi_to_paper:
                        # Merge fetched data with original paper
                        original = doi_to_paper[doi]
                        original['summary'] = fp.get('summary', '')
                        if fp.get('category'):
                            original['category'] = fp['category']
                        if fp.get('journal') and not original.get('journal'):
                            original['journal'] = fp['journal']
                        if fp.get('authors') and not original.get('authors'):
                            original['authors'] = fp['authors']
                        if fp.get('published') and not original.get('published'):
                            original['published'] = fp['published']
                        papers_with_abs.append(original)
                        fetched_dois.add(doi)
            except Exception as e:
                logger.error(f"[{source}] Error fetching batch {i//batch_size + 1}: {e}")
        
        # Add papers that weren't found via API to the without list
        for doi in dois_to_fetch:
            if doi not in fetched_dois:
                papers_without_abs.append(doi_to_paper[doi])
        
        return papers_with_abs, papers_without_abs
    
    def _fetch_nature_api_batch(self, dois: List[str], source: str) -> List[Dict]:
        """
        Fetch abstracts from Nature/Springer API for a batch of DOIs.
        """
        papers = []
        
        api_key = config.NATURE_API_KEY
        if not api_key:
            logger.warning(f"[{source}] NATURE_API_KEY not set, skipping Nature API")
            return papers
        
        try:
            query_str = ' OR '.join([f'doi:"{doi}"' for doi in dois])
            url = f'https://api.springernature.com/meta/v2/pam?api_key={api_key}&callback=&s=1&p=25&q=({query_str})'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.debug(f"[{source}] API request successful, status code: {response.status_code}")
            
            root = ET.fromstring(response.content)
            
            namespaces = {
                'pam': 'http://prismstandard.org/namespaces/pam/2.2/',
                'xhtml': 'http://www.w3.org/1999/xhtml',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'prism': 'http://prismstandard.org/namespaces/basic/2.2/'
            }
            
            articles = root.findall('.//pam:article', namespaces)
            logger.info(f"[{source}] Found {len(articles)} articles in API response")
            
            for idx, article in enumerate(articles):
                paper = self._parse_nature_article(article, namespaces, source, idx)
                if paper:
                    papers.append(paper)
        
        except ET.ParseError as e:
            logger.error(f"[{source}] Error parsing XML: {e}")
        except requests.RequestException as e:
            logger.error(f"[{source}] Request error: {e}")
        except Exception as e:
            logger.error(f"[{source}] Unexpected error: {e}")
        
        return papers
    
    def _parse_nature_article(self, article, namespaces: Dict, source: str, idx: int) -> Optional[Dict]:
        """
        Parse a single article from Nature API response.
        """
        head = article.find('xhtml:head', namespaces)
        if head is None:
            logger.warning(f"[{source}] No head element found for article {idx}")
            return None
        
        doi_elem = head.find('.//prism:doi', namespaces)
        if doi_elem is None or doi_elem.text is None:
            logger.warning(f"[{source}] No DOI found for article {idx}")
            return None
        
        article_doi = doi_elem.text
        
        # Extract abstract from body
        body = article.find('xhtml:body', namespaces)
        abstract_paragraphs = []
        
        if body is not None:
            found_abstract_heading = False
            for elem in body:
                if elem.tag == '{http://www.w3.org/1999/xhtml}h1' and elem.text and 'Abstract' in elem.text:
                    found_abstract_heading = True
                    logger.debug(f"[{source}] Found abstract heading for DOI {article_doi}")
                elif found_abstract_heading and elem.tag == '{http://www.w3.org/1999/xhtml}p':
                    if elem.text:
                        abstract_paragraphs.append(elem.text.strip())
                elif found_abstract_heading and elem.tag == '{http://www.w3.org/1999/xhtml}h1':
                    break
        
        if not abstract_paragraphs:
            logger.debug(f"[{source}] No abstract found for DOI {article_doi}")
            return None
        
        abstract_text = ' '.join(abstract_paragraphs)
        if len(abstract_text) > 3000:
            abstract_text = abstract_text[:3000] + '...'
        
        # Extract metadata
        journal = head.find('.//prism:publicationName', namespaces)
        journal = journal.text if journal is not None else ''
        
        title = head.find('.//dc:title', namespaces)
        title = title.text if title is not None else ''
        
        authors = [a.text for a in head.findall('.//dc:creator', namespaces) if a.text]
        
        published = head.find('.//prism:publicationDate', namespaces)
        published = published.text if published is not None else ''
        
        subjects = head.findall('.//dc:subject', namespaces)
        categories = []
        for subj in subjects:
            if subj.text:
                categories.extend(subj.text.split(', '))
        categories = list(set(categories))
        
        paper = {
            'journal': journal,
            'id': article_doi,
            'pdf': "",
            'abs': f"https://doi.org/{article_doi}",
            'title': title,
            'summary': abstract_text,
            'authors': authors,
            'published': published,
            'category': categories,
        }
        
        logger.debug(f"[{source}] Extracted abstract for DOI {article_doi}")
        return paper
    
    def _try_tavily(self, papers: List[Dict], source: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Try to fetch abstracts using Tavily API with batch processing.
        All paper URLs are sent in a single API call for efficiency.
        
        Returns:
            Tuple of (papers with abstracts, papers without abstracts)
        """
        papers_with_abs = []
        papers_without_abs = []
        
        if not self.tavily_client:
            logger.warning(f"[{source}] Tavily client not available, skipping")
            return [], papers
        
        # Build URL to paper mapping and collect all URLs
        url_to_paper = {}
        urls_to_fetch = []
        
        for paper in papers:
            url = paper.get('abs')
            if not url:
                papers_without_abs.append(paper)
                continue
            urls_to_fetch.append(url)
            url_to_paper[url] = paper
        
        if not urls_to_fetch:
            return papers_with_abs, papers_without_abs
        
        # Batch processing: 20 URLs per batch
        batch_size = 20
        total_batches = (len(urls_to_fetch) + batch_size - 1) // batch_size
        logger.info(f"[{source}] Fetching {len(urls_to_fetch)} URLs via Tavily in {total_batches} batch(es)")
        
        processed_urls = set()  # URLs that got a response from Tavily (success or extraction failed)
        failed_batch_urls = set()  # URLs where Tavily API call failed (should retry)
        
        for batch_idx in range(0, len(urls_to_fetch), batch_size):
            batch_urls = urls_to_fetch[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            logger.info(f"[{source}] Processing batch {batch_num}/{total_batches} ({len(batch_urls)} URLs)")
            
            try:
                # Batch API call for current batch
                response = self.tavily_client.extract(
                    urls=batch_urls,
                    extract_depth="advanced"
                )
                
                if response and response.get('results'):
                    results = response['results']
                    logger.debug(f"[{source}] Batch {batch_num} returned {len(results)} results")
                    
                    # Track which URLs got responses in this batch
                    batch_responded_urls = set()
                    
                    # Process each result and match back to papers
                    for result in results:
                        result_url = result.get('url', '')
                        raw_content = result.get('raw_content', '')
                        
                        # Find matching paper by URL
                        matched_paper = None
                        matched_url = None
                        
                        # Try exact match first
                        if result_url in url_to_paper:
                            matched_paper = url_to_paper[result_url]
                            matched_url = result_url
                        else:
                            # Try partial match (handle URL redirects/variations)
                            for orig_url, paper in url_to_paper.items():
                                if self._urls_match(orig_url, result_url):
                                    matched_paper = paper
                                    matched_url = orig_url
                                    break
                        
                        if matched_paper and matched_url not in processed_urls:
                            batch_responded_urls.add(matched_url)
                            # Extract abstract and categories from raw content
                            abstract, categories = self._extract_from_tavily_content(raw_content, source)
                            
                            # Always mark as processed (Tavily returned data)
                            # If extraction failed, set empty summary - don't retry
                            matched_paper['summary'] = abstract if abstract else ""
                            if categories and not matched_paper.get('category'):
                                matched_paper['category'] = categories
                            papers_with_abs.append(matched_paper)
                            processed_urls.add(matched_url)
                            
                            if abstract:
                                logger.debug(f"[{source}] Extracted abstract for URL: {matched_url}")
                            else:
                                logger.debug(f"[{source}] Tavily returned but no abstract extracted for URL: {matched_url}")
                    
                    # URLs in batch that didn't get a response - should retry
                    for batch_url in batch_urls:
                        if batch_url not in batch_responded_urls and batch_url not in processed_urls:
                            failed_batch_urls.add(batch_url)
                else:
                    # Empty response - all URLs in this batch should retry
                    logger.warning(f"[{source}] Empty Tavily response for batch {batch_num}")
                    for batch_url in batch_urls:
                        if batch_url not in processed_urls:
                            failed_batch_urls.add(batch_url)
                    
            except Exception as e:
                # API error - all URLs in this batch should retry
                logger.error(f"[{source}] Tavily batch {batch_num} API error: {e}")
                for batch_url in batch_urls:
                    if batch_url not in processed_urls:
                        failed_batch_urls.add(batch_url)
        
        # Add papers where Tavily API failed (no response) to retry list
        for url, paper in url_to_paper.items():
            if url not in processed_urls and url in failed_batch_urls:
                papers_without_abs.append(paper)
        
        logger.info(f"[{source}] Tavily total: {len(papers_with_abs)} success, {len(papers_without_abs)} failed")
        return papers_with_abs, papers_without_abs
    
    def _urls_match(self, url1: str, url2: str) -> bool:
        """
        Check if two URLs refer to the same resource.
        Handles DOI redirects and URL variations.
        """
        import re
        
        # Extract DOI from URLs if present
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        
        doi1 = re.search(doi_pattern, url1)
        doi2 = re.search(doi_pattern, url2)
        
        if doi1 and doi2:
            return doi1.group().rstrip('/') == doi2.group().rstrip('/')
        
        # Normalize and compare URLs
        def normalize_url(url):
            url = url.lower().rstrip('/')
            # Remove protocol
            url = re.sub(r'^https?://', '', url)
            # Remove www
            url = re.sub(r'^www\.', '', url)
            return url
        
        return normalize_url(url1) == normalize_url(url2)
    
    def _extract_from_tavily_content(self, text: str, source: str) -> Tuple[str, List[str]]:
        """
        Extract abstract and categories from Tavily raw content.
        
        Returns:
            Tuple of (abstract_text, categories_list)
        """
        if not text:
            return "", []
        
        import re
        
        abstract = ""
        categories = []
        
        # Extract Abstract
        # Pattern 1: Look for "Abstract\n--------" or "Abstract\n" followed by content
        abstract_patterns = [
            # Pattern for academic sites with Abstract heading followed by dashes
            r'Abstract\s*\n[-=]+\s*\n(.+?)(?=\n\d+\.\s|\n[A-Z][A-Z]+\n|© \d{4}|INTRODUCTION|Keywords)',
            # Pattern for "Abstract" followed by text until next major section
            r'\bAbstract\b[:\s]*\n?(.+?)(?=\n\d+\.\s|\n##|\n\*\*[A-Z]|© \d{4}|\n[A-Z]{4,}\n|Introduction\n)',
            # Fallback: Abstract keyword followed by substantial text
            r'\bAbstract\b[:\s]+(.+?)(?=\n\n\d+\.|\n\n[A-Z][a-z]+:)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = self._clean_abstract_text(abstract)
                if len(abstract) > 100:  # Reasonable abstract length
                    break
                else:
                    abstract = ""  # Too short, try next pattern
        
        if len(abstract) > 6000:
            abstract = abstract[:6000]
        
        # Extract Categories/Topics
        # Pattern for "Related Topics" section with links
        topics_patterns = [
            # Optica/OSA style: "*   [Topic Name](url)"
            r'Related Topics.*?\*\s+\[([^\]]+)\]\(https?://[^)]+\)',
            # Generic topic extraction from "Related Topics" section
            r'Related Topics[\s\S]*?(?:\*\s+\[([^\]]+)\])+',
        ]
        
        # Try to find Related Topics section and extract all topics
        related_match = re.search(r'Related Topics[\s\S]*?(?=\n### |\n\*\s+###|About this Article|$)', text, re.IGNORECASE)
        if related_match:
            related_section = related_match.group(0)
            # Extract all bracketed topic names
            topic_matches = re.findall(r'\[([^\]]+)\]\(https?://[^)]+search[^)]*\)', related_section)
            if topic_matches:
                categories = list(set(topic_matches))  # Remove duplicates
        
        # Also try to extract from "Optics & Photonics Topics" section
        if not categories:
            topics_match = re.search(r'Optics & Photonics Topics.*?(?=\n### |\n## |About|$)', text, re.IGNORECASE | re.DOTALL)
            if topics_match:
                section = topics_match.group(0)
                topic_matches = re.findall(r'\[([^\]]+)\]\(https?://[^)]+\)', section)
                if topic_matches:
                    # Filter out navigation/UI links
                    categories = [t for t in topic_matches if len(t) > 3 and not t.startswith('?') and 'http' not in t.lower()]
                    categories = list(set(categories))
        
        logger.debug(f"[{source}] Extracted abstract ({len(abstract)} chars) and {len(categories)} categories")
        return abstract, categories
    
    def _clean_abstract_text(self, text: str) -> str:
        """
        Clean up extracted abstract text.
        """
        import re
        
        # Remove markdown links but keep the text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common noise patterns
        noise_patterns = [
            r'\[\d+\]',  # Reference numbers like [1], [2]
            r'\*\*Fig\..*?\*\*',  # Figure references
            r'Download Full Size.*?PDF',  # Download links
            r'View in Article.*',  # View links
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = ' '.join(text.split())
        
        return text.strip()
