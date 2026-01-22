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
import time
import random
from typing import List, Dict, Optional, Tuple
import requests
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
            papers_with_abs, papers_without_abs, remaining_papers = self._try_nature_api(papers, source)
        else:
            papers_with_abs, papers_without_abs, remaining_papers = [], [], papers
        
        logger.info(f"[{source}] {len(papers_with_abs)} papers found with abstracts from Nature API")
        logger.info(f"[{source}] {len(papers_without_abs)} papers have no abstracts from Nature API")
        if not remaining_papers:
            logger.info(f"[{source}] {len(papers_with_abs)+len(papers_without_abs)} papers fetched successfully from Nature API")
            papers_with_abs.extend(papers_without_abs)
            return papers_with_abs
        logger.info(f"[{source}] {len(remaining_papers)} papers still need to be fetched after Nature API")
        
        # Step 2: Try Tavily for remaining papers with internal retry logic
        tavily_papers, tavily_without_abs, remaining_papers = self._try_tavily(remaining_papers, source)
        
        logger.info(f"[{source}] {len(tavily_papers)} papers found with abstracts from Tavily API")
        logger.info(f"[{source}] {len(tavily_without_abs)} papers have no abstracts from Tavily API")
        papers_with_abs.extend(tavily_papers)
        papers_without_abs.extend(tavily_without_abs)
        if not remaining_papers:
            logger.info(f"[{source}] {len(papers_with_abs)+len(papers_without_abs)} papers fetched successfully from Nature and Tavily API")
            papers_with_abs.extend(papers_without_abs)
            return papers_with_abs
        logger.info(f"[{source}] {len(remaining_papers)} papers still need to be fetched after Tavily API")
        
        logger.info(f"[{source}] Abstract extraction complete: {len([p for p in papers_with_abs if p.get('summary')])} papers with abstracts")
        papers_with_abs.extend(papers_without_abs)  # include those papers without abstracts after all method
        papers_with_abs.extend(remaining_papers)    # include those failed to fetch abstracts
        return papers_with_abs

    def _try_nature_api(self, papers: List[Dict], source: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Try to fetch abstracts using Nature/Springer API with multi-round retry logic.
        
        Returns:
            Tuple of (papers_with_abs, papers_without_abs, paper_failed)
        """
        papers_with_abs = []
        papers_without_abs = []
        paper_failed = []
        
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
            return papers_with_abs, papers_without_abs, paper_failed
        
        logger.info(f"[{source}] Fetching abstracts for {len(dois_to_fetch)} DOIs via Nature API")
        
        remaining_dois = list(dois_to_fetch)
        max_retries = 5
        
        # Round-based retry logic
        for attempt in range(max_retries):
            if not remaining_dois:
                break
                
            if attempt > 0:
                # Exponential backoff: 2^attempt + jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"[{source}] Retrying Nature API (attempt {attempt+1}/{max_retries}) in {wait_time:.2f}s...")
                time.sleep(wait_time)
            
            current_batch_dois = list(remaining_dois)
            batch_size = 20
            
            for i in range(0, len(current_batch_dois), batch_size):
                batch = current_batch_dois[i:i + batch_size]
                logger.info(f"[{source}] Fetching batch {i//batch_size + 1} ({len(batch)} DOIs), attempt {attempt+1}")
                
                try:
                    fetched_papers = self._fetch_nature_api_batch(batch, source)
                    
                    # Success: These DOIs are processed (either found or not found in response)
                    fetched_dois_map = {fp.get('id'): fp for fp in fetched_papers}
                    
                    for doi in batch:
                        if doi in remaining_dois:
                            remaining_dois.remove(doi)
                        
                        original = doi_to_paper[doi]
                        if doi in fetched_dois_map:
                            fp = fetched_dois_map[doi]
                            # Merge fetched data with original paper
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
                        else:
                            # Not found in successful API response - don't retry as per requirements
                            logger.debug(f"[{source}] DOI {doi} not found in Nature API response")
                            papers_without_abs.append(original)
                            
                except Exception as e:
                    # Request failed, empty response, or parsing error - keep DOIs for next round retry
                    logger.warning(f"[{source}] Batch attempt {i//batch_size + 1} failed (round {attempt+1}): {e}")
                    # DOIs remain in remaining_dois and will be picked up in next attempt loop
        
        # After all retries, any remaining DOIs are considered permanently failed
        if remaining_dois:
            for doi in remaining_dois:
                paper = doi_to_paper[doi]
                paper_failed.append(paper)
                logger.error(f"[{source}] Nature API failed after {max_retries} attempts for DOI: {doi}. Last error info: {paper.get('abs')}")
        
        return papers_with_abs, papers_without_abs, paper_failed
    
    def _fetch_nature_api_batch(self, dois: List[str], source: str) -> List[Dict]:
        """
        Fetch abstracts from Nature/Springer API for a batch of DOIs.
        
        Raises:
            requests.RequestException: If the network request fails or returns error status.
            ValueError: If the response is empty or invalid JSON.
        """
        papers = []
        
        api_key = config.NATURE_API_KEY
        if not api_key:
            logger.warning(f"[{source}] NATURE_API_KEY not set, skipping Nature API")
            return papers
        
        query_str = ' OR '.join([f'doi:"{doi}"' for doi in dois])
        url = f'https://api.springernature.com/metadata/json?api_key={api_key}&callback=&s=1&p=25&q=({query_str})'
        
        response = requests.get(url, timeout=30)
        
        # Log response status
        logger.debug(f"[{source}] Nature API request: {url} | Status: {response.status_code}")
        
        response.raise_for_status()
        
        if not response.content:
            raise ValueError("Empty response content from Nature API")
            
        try:
            data = response.json()
            records = data.get('records', [])
            logger.info(f"[{source}] Found {len(records)} articles in API response")
            
            for idx, record in enumerate(records):
                paper = self._parse_nature_article(record, source, idx)
                if paper:
                    papers.append(paper)
        except Exception as e:
            logger.error(f"[{source}] Error parsing JSON from Nature API: {e}")
            raise
        
        return papers
    
    def _parse_nature_article(self, record: Dict, source: str, idx: int) -> Optional[Dict]:
        """
        Parse a single article from Nature API JSON response.
        """
        article_doi = record.get('doi')
        if not article_doi:
            # Fallback to identifier if doi is missing
            identifier = record.get('identifier', '')
            if identifier.startswith('doi:'):
                article_doi = identifier.replace('doi:', '')
            else:
                logger.warning(f"[{source}] No DOI found for article {idx}")
                return None
        
        # Extract abstract
        abstract_text = record.get('abstract', '')
        
        if not abstract_text:
            logger.debug(f"[{source}] No abstract found for DOI {article_doi}")
            return None
            
        if isinstance(abstract_text, str) and len(abstract_text) > 3000:
            abstract_text = abstract_text[:3000] + '...'
        
        # Extract metadata
        journal = record.get('publicationName', '')
        title = record.get('title', '')
        
        creators = record.get('creators', [])
        authors = [c.get('creator', '') for c in creators if c.get('creator')]
        
        published = record.get('publicationDate', '')
        categories = record.get('subjects', [])
        
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
    
    def _try_tavily(self, papers: List[Dict], source: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Try to fetch abstracts using Tavily API with batch processing and multi-round retry logic.
        
        Returns:
            Tuple of (papers_with_abs, papers_without_abs, paper_failed)
        """
        papers_with_abs = []
        papers_without_abs = []
        paper_failed = []
        
        if not self.tavily_client:
            logger.warning(f"[{source}] Tavily client not available, skipping")
            return [], papers, []
        
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
            return papers_with_abs, papers_without_abs, paper_failed
        
        logger.info(f"[{source}] Fetching {len(urls_to_fetch)} URLs via Tavily")
        
        remaining_urls = list(urls_to_fetch)
        max_retries = 5
        
        # Round-based retry logic
        for attempt in range(max_retries):
            if not remaining_urls:
                break
                
            if attempt > 0:
                # Exponential backoff: 2^attempt + jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"[{source}] Retrying Tavily API (attempt {attempt+1}/{max_retries}) in {wait_time:.2f}s...")
                time.sleep(wait_time)
            
            current_round_urls = list(remaining_urls)
            batch_size = 20
            
            for batch_idx in range(0, len(current_round_urls), batch_size):
                batch_urls = current_round_urls[batch_idx:batch_idx + batch_size]
                batch_num = batch_idx // batch_size + 1
                logger.info(f"[{source}] Processing Tavily batch {batch_num} ({len(batch_urls)} URLs), attempt {attempt+1}")
                
                try:
                    # Batch API call for current batch
                    response = self.tavily_client.extract(
                        urls=batch_urls,
                        extract_depth="advanced"
                    )
                    
                    if not response or not response.get('results'):
                        # Empty response - will retry in next round
                        logger.warning(f"[{source}] Empty Tavily response for batch {batch_num} (round {attempt+1})")
                        continue

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
                        
                        if matched_paper and matched_url in remaining_urls:
                            batch_responded_urls.add(matched_url)
                            remaining_urls.remove(matched_url)
                            
                            # Extract abstract and categories from raw content
                            abstract, categories = self._extract_from_tavily_content(raw_content, source)
                            
                            # Always mark as processed (Tavily returned data)
                            # If extraction failed, set empty summary - don't retry as per requirements
                            matched_paper['summary'] = abstract if abstract else ""
                            if categories and not matched_paper.get('category'):
                                matched_paper['category'] = categories
                            
                            if abstract:
                                papers_with_abs.append(matched_paper)
                                logger.debug(f"[{source}] Extracted abstract for URL: {matched_url}")
                            else:
                                papers_without_abs.append(matched_paper)
                                logger.debug(f"[{source}] Tavily returned but no abstract extracted for URL: {matched_url}")
                    
                    # URLs in batch that didn't get a response will remain in remaining_urls for next round retry
                    
                except Exception as e:
                    # API error - all URLs in this batch will remain in remaining_urls for next round retry
                    logger.error(f"[{source}] Tavily batch {batch_num} API error (round {attempt+1}): {e}")
        
        # After all retries, any remaining URLs are considered permanently failed
        if remaining_urls:
            for url in remaining_urls:
                paper = url_to_paper[url]
                paper_failed.append(paper)
                logger.error(f"[{source}] Tavily API failed after {max_retries} attempts for URL: {url}")
        
        logger.info(f"[{source}] Tavily final results: {len(papers_with_abs)} success, {len(papers_without_abs)} no abstract found, {len(paper_failed)} failed")
        return papers_with_abs, papers_without_abs, paper_failed
    
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
        
        # Determine which extractor to use based on URL or source
        abstract = ""
        
        if source == "science":
            abstract = self._extract_science(text)
        elif source == "nature":
            abstract = self._extract_nature(text)
        elif source == "aps":
            abstract = self._extract_aps(text)
        elif source == "optica":
            abstract = self._extract_optica(text)
        elif source == "sciencedirect":
            abstract = self._extract_sciencedirect(text)
        elif source == "pubmed":
            abstract = self._extract_pubmed(text)
        else:
            abstract = self._extract_generic(text)
        
        # If specific extractor failed, try generic
        if not abstract:
            abstract = self._extract_generic(text)
            
        # Extract Categories/Topics (generic logic for now as it's common across sources)
        categories = self._extract_categories_generic(text)
        
        logger.debug(f"[{source}] Extracted abstract ({len(abstract)} chars) and {len(categories)} categories")
        return abstract, categories

    def _extract_science(self, text: str) -> str:
          """Specific extractor for Science journals."""
          import re
          # Science usually has "Abstract" section. 
          # User requirement: Extract "Abstract", ignore "Structured Abstract" and "Editor's summary".
          
          # Strategy: Find all "Abstract" occurrences and pick the one that is NOT structured
          # The plain abstract usually comes after Structured Abstract if both exist, 
          # or it might be the only one.
          
          # Pattern to match "Abstract" header (possibly with # or dashes)
          # We look for "Abstract" that isn't preceded by "Structured "
          # And it should be followed by a block of text, not just links.
          
          # First, let's try to find the one that is clearly a section header
          patterns = [
              # Match ## Abstract or ### Abstract
              r'## Abstract\s*\n\s*(.+?)(?=\n\s*(?:##|###|Access|Supplementary|References|Information|Metrics))',
              # Match Abstract followed by dashes
              r'Abstract\s*\n[= \-]+\n\s*(.+?)(?=\n\s*(?:##|###|Access|Supplementary|References|Information|Metrics))',
              # Fallback: Just "Abstract" as a line
              r'\nAbstract\n\s*(.+?)(?=\n\s*(?:##|###|Access|Supplementary|References|Information|Metrics))',
          ]
          
          for pattern in patterns:
              matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
              for match in matches:
                  content = match.group(1).strip()
                  # Filter out "Structured Abstract" and "Editor's summary" if they accidentally matched
                  # and ensure it's not just a list of links (common in Science sidebar)
                  if len(content) > 150 and "INTRODUCTION" not in content[:200] and "Editor’s summary" not in content and "This website requires cookies to function properly" not in content:
                      return self._clean_abstract_text(content)
          
          return ""

    def _extract_nature(self, text: str) -> str:
        """Specific extractor for Nature journals."""
        import re
        # Nature usually has "Abstract" then content, then "Access options" or "Introduction"
        patterns = [
            r'Abstract\s*\n[= \-]+\n\s*(.+?)(?=\n\s*(?:Access options|Introduction|Methods|References|### |Rights and permissions))',
            r'Abstract\s*\n\s*(.+?)(?=\n\s*(?:Access options|Introduction|Methods|References|### ))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > 150:
                    return self._clean_abstract_text(content)
        return ""

    def _extract_aps(self, text: str) -> str:
        """Specific extractor for APS journals (Physical Review, etc.)."""
        import re
        # APS usually has "Abstract" then content, then "Received" or "Published"
        patterns = [
            r'Abstract\s*\n[= \-]+\n\s*(.+?)(?=\n\s*(?:Received|Published|DOI:|Introduction|### ))',
            r'Abstract\s*\n\s*(.+?)(?=\n\s*(?:Received|Published|DOI:|Introduction|### ))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > 150:
                    return self._clean_abstract_text(content)
        return ""

    def _extract_optica(self, text: str) -> str:
         """Specific extractor for Optica (formerly OSA) journals."""
         import re
         # Optica/OSA often has "Abstract" followed by content
         patterns = [
             # Look for Abstract followed by dashes, then content until copyright or next section
             r'Abstract\s*\n[= \-]+\n\s*(.+?)(?=\n\s*(?:©|Introduction|Methods|References|###|Related Topics))',
             # Simpler version without dashes
             r'Abstract\s*\n\s*(.+?)(?=\n\s*(?:©|Introduction|Methods|References|###))',
             # Fallback: Just take everything after the "Abstract" with dashes until a large gap or end
             r'Abstract\s*\n[= \-]+\n\s*(.+?)(?=\n\n\n|$)',
         ]
         for pattern in patterns:
             match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
             if match:
                 content = match.group(1).strip()
                 if len(content) > 150:
                     return self._clean_abstract_text(content)
         return ""

    def _extract_sciencedirect(self, text: str) -> str:
        """Specific extractor for ScienceDirect."""
        import re
        # ScienceDirect often uses "Abstract" or "Summary"
        patterns = [
            r'Abstract\s*\n\s*(.+?)(?=\n\s*(?:Keywords|Introduction|Methods|Results|### ))',
            r'Summary\s*\n\s*(.+?)(?=\n\s*(?:Keywords|Introduction|### ))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > 150:
                    return self._clean_abstract_text(content)
        return ""

    def _extract_pubmed(self, text: str) -> str:
        """Specific extractor for PubMed."""
        import re
        # PubMed uses "Abstract" or sections
        patterns = [
            r'Abstract\s*\n\s*(.+?)(?=\n\s*(?:Similar articles|Cited by|MeSH terms|### ))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > 150:
                    return self._clean_abstract_text(content)
        return ""

    def _extract_generic(self, text: str) -> str:
        """Generic extractor for unknown sources."""
        import re
        abstract_patterns = [
            # Pattern for academic sites with Abstract heading followed by dashes
            r'Abstract\s*\n[-=]+\s*\n(.+?)(?=\n\d+\.\s|\n[A-Z][A-Z]+\n|© \d{4}|INTRODUCTION|Keywords|References)',
            # Pattern for "Abstract" followed by text until next major section
            r'\bAbstract\b[:\s]*\n?(.+?)(?=\n\d+\.\s|\n##|\n\*\*[A-Z]|© \d{4}|\n[A-Z]{4,}\n|Introduction\n)',
            # Fallback: Abstract keyword followed by substantial text
            r'\bAbstract\b[:\s]+(.+?)(?=\n\n\d+\.|\n\n[A-Z][a-z]+:)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                abstract = self._clean_abstract_text(abstract)
                if len(abstract) > 150:
                    return abstract
        
        # Final fallback: if no "Abstract" keyword, but there is substantial text
        # (This is risky but sometimes necessary)
        if len(text) > 500 and len(text) < 10000:
            # Just return a cleaned version of the first part of text if it's not too large
            return self._clean_abstract_text(text[:2000])
            
        return ""

    def _extract_categories_generic(self, text: str) -> List[str]:
        """Generic category extraction logic."""
        import re
        categories = []
        
        # Try to find Related Topics section and extract all topics
        related_match = re.search(r'Related Topics[\s\S]*?(?=\n### |\n\*\s+###|About this Article|$)', text, re.IGNORECASE)
        if related_match:
            related_section = related_match.group(0)
            # Extract all bracketed topic names
            topic_matches = re.findall(r'\[([^\]]+)\]\(https?://[^)]+search[^)]*\)', related_section)
            if topic_matches:
                categories = list(set(topic_matches))
        
        # Also try to extract from "Optics & Photonics Topics" section
        if not categories:
            topics_match = re.search(r'Optics & Photonics Topics.*?(?=\n### |\n## |About|$)', text, re.IGNORECASE | re.DOTALL)
            if topics_match:
                section = topics_match.group(0)
                topic_matches = re.findall(r'\[([^\]]+)\]\(https?://[^)]+\)', section)
                if topic_matches:
                    categories = [t for t in topic_matches if len(t) > 3 and not t.startswith('?') and 'http' not in t.lower()]
                    categories = list(set(categories))
                    
        return categories
    
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
