"""Generic RSS Fetcher for academic papers with caching mechanism.

This module provides a generic RSS fetcher that can handle various journal RSS feeds.
Currently implemented sources:
    - arXiv RSS feeds

The fetcher implements a caching system to track previously fetched papers.
Only new papers are appended to the output file.

Multi-Source Support:
    - Accepts comma-separated list of sources via --sources parameter
    - Each source gets its own cache file: rss_cache_{source}.json
    - Each source gets its own output file: {basename}_{source}.jsonl
    - All sources share unified logging output

Caching Strategy:
    - Paper IDs are cached in data/rss_cache_{source}.json (per source)
    - Each run checks both the cache and existing output file
    - Only papers with new IDs are appended to the output file
    - Cache is updated after each successful fetch

Usage:
    Single source:
        fetcher = RSSFetcher(source='arxiv', categories='cs.AI')
        papers = fetcher.fetch()
    
    Multiple sources (CLI):
        python rss_fetcher.py --sources arxiv,nature --categories cs.AI --output 2025-10-31
        # Generates: 2025-10-31_arxiv.jsonl, 2025-10-31_nature.jsonl
        # Cache files: rss_cache_arxiv.json, rss_cache_nature.json
"""

import feedparser
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time
import xml.etree.ElementTree as ET
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from fetcher.abstract_extracter import AbstractExtractor
# from abstract_extracter import AbstractExtractor


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger

logger = get_logger(__name__)


class RSSFetcher:
    """
    Generic RSS fetcher for academic papers from various sources.
    
    Supported sources:
        - 'arxiv': arXiv RSS feeds
    
    Args:
        source: Source type ('arxiv', etc.)
        categories: Categories/subjects to fetch (format depends on source)
        cache_dir: Directory to store cache files
    """
    
    SUPPORTED_SOURCES = ['arxiv', 'nature', 'science', 'optica', 'aps']
    
    def __init__(self, source: str = 'arxiv', categories: str = '', cache_dir: str = "data/cache"):
        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported source: {source}. Supported sources: {self.SUPPORTED_SOURCES}")
        
        self.source = source
        self.categories = categories
        self.cache_dir = Path(cache_dir)
        # Source-specific cache file
        self.cache_file = self.cache_dir / f"rss_cache_{source}.json"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize source-specific configuration
        self._init_source_config()
        
        logger.info(f"Initialized RSSFetcher with source: {source}, categories: {categories}")
        logger.info(f"Cache file: {self.cache_file}")
    
    def _init_source_config(self):
        """Initialize source-specific configuration."""
        if self.source == 'arxiv':
            self.base_url = "https://rss.arxiv.org/rss/"
            logger.debug(f"Configured arXiv RSS base URL: {self.base_url}")
        elif self.source == 'nature':
            self.base_url = "https://www.nature.com/"
            logger.debug(f"Configured Nature RSS base URL: {self.base_url}")
        elif self.source == 'science':
            self.base_url = "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc="
            logger.debug(f"Configured Science RSS base URL: {self.base_url}")
        elif self.source == 'optica':
            self.base_url = "https://opg.optica.org/rss/"
            logger.debug(f"Configured Optica RSS base URL: {self.base_url}")
        elif self.source == 'aps':
            self.base_url = "https://feeds.aps.org/rss/recent/"
            logger.debug(f"Configured APS RSS base URL: {self.base_url}")
        # Add more sources here in the future
        # Example for adding a new source:
        # elif self.source == 'science':
        #     self.base_url = "https://www.science.org/rss/"
        #     logger.debug(f"Configured Science RSS base URL: {self.base_url}")
    
    def load_cache(self) -> Set[str]:
        """
        Load cached paper IDs from the cache file.
        
        Returns:
            Set of paper IDs that have been previously fetched
        """
        if not self.cache_file.exists():
            logger.info("No cache file found, starting fresh")
            return set()
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cached_ids = set(cache_data.get('paper_ids', []))
                logger.info(f"Loaded {len(cached_ids)} cached paper IDs")
                return cached_ids
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load cache file: {e}, starting fresh")
            return set()
    
    def save_cache(self, paper_ids: Set[str]):
        """
        Save paper IDs to the cache file.
        
        Args:
            paper_ids: Set of all paper IDs to cache
        """
        try:
            cache_data = {
                'paper_ids': list(paper_ids),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(paper_ids)} paper IDs to cache")
        except IOError as e:
            logger.error(f"Failed to save cache file: {e}")   
            raise 

    def fetch(self, date: str | None = None) -> List[Dict]:
        """
        Fetch papers from the RSS feed.
        
        Args:
            date: Optional date parameter (implementation depends on source)
            
        Returns:
            List of paper dictionaries
        """
        if self.source == 'arxiv':
            return self._fetch_arxiv()
        elif self.source == 'nature':
            return self._fetch_nature()
        elif self.source == 'science':
            return self._fetch_science()
        elif self.source == 'optica':
            return self._fetch_optica()
        elif self.source == 'aps':
            return self._fetch_aps()
        # Example for adding a new source:
        # elif self.source == 'science':
        #     return self._fetch_science()
        else:
            raise NotImplementedError(f"Fetch not implemented for source: {self.source}")
    
    def _fetch_arxiv(self) -> List[Dict]:
        """
        Fetch papers from arXiv RSS feed.
        
        Returns:
            List of paper dictionaries with arXiv-specific fields
        """
        papers = []
        seen_ids = set()
        
        rss_url = f"{self.base_url}{self.categories}"
        logger.info(f"Fetching arXiv RSS feed from: {rss_url}")
        
        try:
            response = requests.get(rss_url, timeout=30)
            response.raise_for_status()
            logger.debug(f"RSS feed fetched successfully, status code: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch RSS feed: {e}")
            raise
        
        feed = feedparser.parse(response.content)
        logger.info(f"Parsed feed with {len(feed.entries)} entries")
        
        for entry in feed.entries:
            arxiv_id = entry.id.split('.org:')[-1]
            
            if arxiv_id in seen_ids:
                logger.debug(f"Skipping duplicate paper: {arxiv_id}")
                continue
            
            seen_ids.add(arxiv_id)
            logger.debug(f"Processing paper: {arxiv_id}")
            publish_date = entry.published if hasattr(entry, 'published') else '',
            publish_date = publish_date[0].split(' ')
            publish_date = datetime.strptime(publish_date[1]+' '+publish_date[2]+' '+publish_date[3], "%d %b %Y").strftime("%Y-%m-%d")
            
            authors_p = [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
            authors = sum([author.split(', ') for author in authors_p], []) if authors_p else []
            authors = [author for author in authors if author]  # Remove empty strings

            paper = {
                'journal': 'ArXiv',
                'id': arxiv_id,
                'pdf': f"https://arxiv.org/pdf/{arxiv_id}",
                'abs': f"https://arxiv.org/abs/{arxiv_id}",        # if RSS has abstract use original link
                'title': entry.title,
                'summary': entry.summary.split('\nAbstract: ')[-1],
                'authors': authors,
                'published': publish_date,
                'category': [entry.category],
            }
            papers.append(paper)
        
        logger.info(f"Successfully fetched {len(papers)} unique papers from arXiv")
        return papers
    
    def _fetch_nature(self) -> List[Dict]:
        """
        Fetch papers from Nature RSS feed.
        
        Returns:
            List of paper dictionaries with Nature-specific fields
        """
        papers = []
        seen_ids = set()

        categories = self.categories.split('+')
        
        for category in categories:
            time.sleep(1)
            rss_url = f"{self.base_url}{category}.rss"
            logger.info(f"Fetching {self.source} RSS feed from: {rss_url}")
            
            try:
                response = requests.get(rss_url, timeout=30)
                response.raise_for_status()
                logger.debug(f"RSS feed fetched successfully, status code: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch RSS feed: {e}")
                raise
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # Extract paper ID (format depends on source)
                # paper_id = entry.prism_doi  # Adjust based on source
                paper_id = entry.prism_doi  # Adjust based on source
                
                if paper_id in seen_ids:
                    continue
                
                seen_ids.add(paper_id)
                logger.debug(f"Processing paper: {paper_id}")

                publish_date = entry.updated if hasattr(entry, 'updated') else ''
                
                authors_p = [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
                authors = sum([author.split(', ') for author in authors_p], []) if authors_p else []
                authors = [author for author in authors if author]  # Remove empty strings
                
                paper = {
                    'journal': entry.prism_publicationname if hasattr(entry, 'prism_publicationname') else '',
                    'id': paper_id,
                    'pdf': "",
                    'abs': f"https://doi.org/{entry.prism_doi}",      # if RSS has no abstract use doi link
                    'title': entry.title,
                    'summary': '',
                    'authors': authors,
                    'published': publish_date,
                    'category': [],
                }
                papers.append(paper)
        
        logger.info(f"Successfully fetched {len(papers)} unique papers from {self.source}")
        return papers

    def _fetch_science(self) -> List[Dict]:
        """
        Fetch papers from Science RSS feed.
        
        Returns:
            List of paper dictionaries with Science-specific fields
        """
        papers = []
        seen_ids = set()

        categories = self.categories.split('+')
        
        for category in categories:
            time.sleep(1)
            rss_url = f"{self.base_url}{category}"
            logger.info(f"Fetching {self.source} RSS feed from: {rss_url}")
            
            try:
                response = requests.get(rss_url, timeout=30)
                response.raise_for_status()
                logger.debug(f"RSS feed fetched successfully, status code: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch RSS feed: {e}")
                raise
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # Extract paper ID (format depends on source)
                # paper_id = entry.prism_doi  # Adjust based on source
                paper_id = entry.prism_doi  # Adjust based on source
                
                if paper_id in seen_ids:
                    continue
                
                seen_ids.add(paper_id)
                logger.debug(f"Processing paper: {paper_id}")

                publish_date = entry.updated if hasattr(entry, 'updated') else ''
                publish_date = datetime.strptime(publish_date, '%Y-%m-%dT%H:%M:%SZ').strftime("%Y-%m-%d")
                
                authors_p = [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
                authors = sum([author.split(', ') for author in authors_p], []) if authors_p else []
                authors = [author for author in authors if author]  # Remove empty strings
                
                paper = {
                    'journal': entry.prism_publicationname if hasattr(entry, 'prism_publicationname') else '',
                    'id': paper_id,
                    'pdf': "",
                    'abs': f"https://doi.org/{entry.prism_doi}",      # if RSS has no abstract use doi link
                    'title': entry.title,
                    'summary': '',
                    'authors': authors,
                    'published': publish_date,
                    'category': [],
                }
                papers.append(paper)
        
        logger.info(f"Successfully fetched {len(papers)} unique papers from {self.source}")
        return papers

    def _fetch_optica(self) -> List[Dict]:
        """
        Fetch papers from Optica RSS feed.
        
        Returns:
            List of paper dictionaries with Optica-specific fields
        """
        papers = []
        seen_ids = set()

        categories = self.categories.split('+')
        
        for category in categories:
            time.sleep(1)
            rss_url = f"{self.base_url}{category}_feed.xml"
            logger.info(f"Fetching {self.source} RSS feed from: {rss_url}")
            
            try:
                response = requests.get(rss_url, timeout=30)
                response.raise_for_status()
                logger.debug(f"RSS feed fetched successfully, status code: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch RSS feed: {e}")
                raise
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # Extract paper ID (format depends on source)
                # paper_id = entry.prism_doi  # Adjust based on source
                paper_id = entry.dc_identifier.split('doi:')[-1]  # Adjust based on source
                
                if paper_id in seen_ids:
                    continue
                
                seen_ids.add(paper_id)
                logger.debug(f"Processing paper: {paper_id}")

                publish_date = entry.published if hasattr(entry, 'published') else ''
                publish_date = publish_date.split(' ') if publish_date else ''
                publish_date = datetime.strptime(publish_date[1]+' '+publish_date[2]+' '+publish_date[3], "%d %b %Y").strftime("%Y-%m-%d")
                
                authors_p = [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
                authors = sum([author.split(', ') for author in authors_p], []) if authors_p else []
                authors = [author for author in authors if author]  # Remove empty strings

                journal = entry.dc_source if hasattr(entry, 'dc_source') else ''
                journal = journal.split(',')[0] if journal else ''
                
                paper = {
                    'journal': journal,
                    'id': paper_id,
                    'pdf': "",
                    'abs': f"https://doi.org/{paper_id}",      # if RSS has no abstract use doi link
                    'title': entry.title,
                    'summary': '',
                    'authors': authors,
                    'published': publish_date,
                    'category': [],
                }
                papers.append(paper)
        
        logger.info(f"Successfully fetched {len(papers)} unique papers from {self.source}")
        return papers

    def _fetch_aps(self) -> List[Dict]:
        """
        Fetch papers from APS RSS feed.
        
        Returns:
            List of paper dictionaries with APS-specific fields
        """
        papers = []
        seen_ids = set()

        categories = self.categories.split('+')
        
        for category in categories:
            time.sleep(1)
            rss_url = f"{self.base_url}{category}.xml"
            logger.info(f"Fetching {self.source} RSS feed from: {rss_url}")
            
            try:
                response = requests.get(rss_url, timeout=30)
                response.raise_for_status()
                logger.debug(f"RSS feed fetched successfully, status code: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch RSS feed: {e}")
                raise
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                # Extract paper ID (format depends on source)
                # paper_id = entry.prism_doi  # Adjust based on source
                paper_id = entry.prism_doi  # Adjust based on source
                
                if paper_id in seen_ids:
                    continue
                
                seen_ids.add(paper_id)
                logger.debug(f"Processing paper: {paper_id}")

                publish_date = entry.prism_publicationdate if hasattr(entry, 'prism_publicationdate') else ''
                publish_date = datetime.strptime(publish_date.split('+')[0], '%Y-%m-%dT%H:%M:%S').strftime("%Y-%m-%d")
                
                authors_p = [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
                authors = sum([author.split(', ') for author in authors_p], []) if authors_p else []
                authors = [author for author in authors if author]  # Remove empty strings
                if authors:
                    if len(authors[-1])>4:
                        if authors[-1][0:4] == 'and ':
                            authors[-1] = authors[-1][4:] if authors[-1][0:4] == 'and ' else authors[-1]

                subject = entry.prism_section if hasattr(entry, 'prism_section') else ''
                categories = subject.split(', ') if subject else ''
                categories = [category for category in categories if category]  # Remove empty strings
                if categories:
                    if len(categories[-1])>4:
                        if categories[-1][0:4] == 'and ':
                            categories[-1] = categories[-1][4:] 
                
                paper = {
                    'journal': entry.prism_publicationname if hasattr(entry, 'prism_publicationname') else '',
                    'id': paper_id,
                    'pdf': "",
                    'abs': f"https://doi.org/{entry.prism_doi}",      # if RSS has no abstract use doi link
                    'title': entry.title,
                    'summary': '',
                    'authors': authors,
                    'published': publish_date,
                    'category': categories,
                }
                papers.append(paper)
        
        logger.info(f"Successfully fetched {len(papers)} unique papers from {self.source}")
        return papers
    
    def save_to_jsonl(self, papers: List[Dict], output_file: str, append: bool = False):
        """
        Save papers to JSONL file.
        
        Args:
            papers: List of papers to save
            output_file: Path to output file
            append: If True, append to existing file; if False, overwrite
        """
        mode = 'a' if append else 'w'
        action = "Appending" if append else "Saving"
        logger.info(f"{action} {len(papers)} papers to {output_file}")
        
        try:
            with open(output_file, mode, encoding='utf-8') as f:
                for paper in papers:
                    f.write(json.dumps(paper, ensure_ascii=False) + '\n')
            logger.info(f"Successfully saved papers to {output_file}")
        except IOError as e:
            logger.error(f"Failed to save papers to {output_file}: {e}")
            raise

def get_abstract(source, article_dois):
    """
    Extract the abstract of a paper from an official API.
    
    Args:
        source: Source name (e.g., 'nature')
        article_dois: List of DOIs of the papers
    Returns:
        List[str]: List of extracted abstract texts (one per DOI)
    """
    papers_with_abs = []

    if source == 'nature':
        # Fetch abstracts in batches of 25
        batch_size = 20

        for i in range(0, len(article_dois), batch_size):
            batch = article_dois[i:i + batch_size]
            logger.info(f"[{source}] Fetching abstracts for batch {i//batch_size + 1} ({len(batch)} DOIs)")

            try:
                query_str = ' OR '.join([f'doi:"{doi}"' for doi in batch])
                url = f'https://api.springernature.com/meta/v2/pam?api_key={os.environ.get("NATURE_API_KEY")}&callback=&s=1&p=25&q=({query_str})'
                response = requests.request("GET", url)
                response.raise_for_status()
                logger.debug(f"API request successful, status code: {response.status_code}")

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
                    # Extract DOI from article
                    head = article.find('xhtml:head', namespaces)
                    if head is None:
                        logger.warning(f"[{source}] No head element found for article {idx}")
                        continue
                    
                    doi_elem = head.find('.//prism:doi', namespaces)
                    if doi_elem is None or doi_elem.text is None:
                        logger.warning(f"[{source}] No DOI found for article {idx}")
                        continue
                    
                    article_doi = doi_elem.text
                    
                    # Extract abstract from body
                    body = article.find('xhtml:body', namespaces)
                    abstract_paragraphs = []
                    
                    if body is not None:
                        found_abstract_heading = False
                        # Iterate through body elements to find abstract
                        for elem in body:
                            # Check for Abstract heading
                            if elem.tag == '{http://www.w3.org/1999/xhtml}h1' and elem.text and 'Abstract' in elem.text:
                                found_abstract_heading = True
                                logger.debug(f"[{source}] Found abstract heading for DOI {article_doi}")
                            # Collect all paragraph elements after Abstract heading
                            elif found_abstract_heading and elem.tag == '{http://www.w3.org/1999/xhtml}p':
                                if elem.text:
                                    abstract_paragraphs.append(elem.text.strip())
                            # Stop when hitting next heading (end of abstract section)
                            elif found_abstract_heading and elem.tag == '{http://www.w3.org/1999/xhtml}h1':
                                break
                    
                        # Store abstract if found
                        if abstract_paragraphs:
                            abstract_text = ' '.join(abstract_paragraphs)
                            journal = head.find('.//prism:publicationName', namespaces).text if head.find('.//prism:publicationName', namespaces) is not None else ''
                            title = head.find('.//dc:title', namespaces).text if head.find('.//dc:title', namespaces) is not None else ''
                            authors = [author.text for author in head.findall('.//dc:creator', namespaces)] if head.findall('.//dc:creator', namespaces) is not None else []
                            published = head.find('.//prism:publicationDate', namespaces).text if head.find('.//prism:publicationDate', namespaces) is not None else ''
                            categoris = list(set(sum([category.text.split(', ') for category in head.findall('.//dc:subject', namespaces)], []))) if head.findall('.//dc:subject', namespaces) is not None else ''
                            # Limit abstract length to 3000 characters
                            if len(abstract_text) > 3000:
                                abstract_text = abstract_text[:3000] + '...'
                            paper = {
                                'journal': journal,
                                'id': article_doi,
                                'pdf': "",
                                'abs': f"https://doi.org/{article_doi}",      # if RSS has no abstract use doi link
                                'title': title,
                                'summary': abstract_text,
                                'authors': authors,
                                'published': published,
                                'category': categoris,
                            }
                            papers_with_abs.append(paper)
                            logger.debug(f"[{source}] Extracted abstract for DOI {article_doi}")
                        else:
                            logger.warning(f"[{source}] No abstract found for DOI {article_doi}")
                    else:
                        logger.warning(f"[{source}] No body element found for article {idx}")
                        
                logger.info(f"[{source}] Processed batch {i//batch_size + 1}: {len(papers_with_abs)} abstracts extracted")

            except ET.ParseError as e:
                logger.error(f"Error parsing XML for batch {i//batch_size + 1}: {e}")
                raise
                # Add empty abstracts for this batch
            except requests.RequestException as e:
                logger.error(f"Error fetching abstracts for batch {i//batch_size + 1}: {e}")
                raise
                # Add empty abstracts for this batch
            except Exception as e:
                logger.error(f"Unexpected error fetching abstracts for batch {i//batch_size + 1}: {e}")
                raise
                # Add empty abstracts for this batch
    else:
        logger.error(f"Unsupported source: {source}")
        raise NotImplementedError(f"Fetch abstract not implemented for source: {source}")

    return papers_with_abs

############# Not Finished yet
def extract_abstract(source, soup: BeautifulSoup):
    logger.debug(f"[{source}] Extracting abstract from {source} page")
    abstract_tag = soup.find("h2", string=lambda text: text and "abstract" in text.lower())
    if abstract_tag:
        # Try to get the next sibling or parent container that holds the abstract text
        abstract_content = ""
        next_sib = abstract_tag.find_next_sibling()
        if next_sib:
            abstract_content = next_sib.get_text(strip=True)
            logger.debug(f"[{source}] Abstract extracted from next sibling")
        else:
            # Fallback: look for a parent section and extract text
            parent = abstract_tag.find_parent(["section", "div"])
            if parent:
                abstract_content = parent.get_text(strip=True)
                logger.debug(f"[{source}] Abstract extracted from parent element")
    else:
        # Try to extract from <meta name="dc.description" ...>
        meta_tag = soup.find("meta", attrs={"name": "dc.description"})
        if meta_tag and meta_tag.get("content"):
            abstract_content = meta_tag["content"]
            logger.debug(f"[{source}] Abstract extracted from meta tag")
        else:
            abstract_content = ""
            logger.debug(f"[{source}] Failed to extract abstract from {source} page")
    return abstract_content

async def get_metadata_crawler(source, url: str):
    logger.debug(f"[{source}] Starting web crawler for {source}: {url}")
    # 1) Reference your persistent data directory
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
        # headless=True,
        # verbose=True,
        use_managed_browser=True,  # Enables persistent browser strategy
        browser_type="chromium",
        # user_data_dir="data\\my_chrome_profile"
    )
    run_config = CrawlerRunConfig(
        delay_before_return_html=1
    )
    logger.debug(f"[{source}] Browser config initialized")

    async with AsyncWebCrawler(config=browser_config) as crawler:
    # async with AsyncWebCrawler() as crawler:
        logger.debug(f"[{source}] Crawling URL: {url}")
        result = await crawler.arun(
            url=url,
            run_config=run_config
        )
        if result.success:
            logger.debug(f"[{source}] Successfully crawled {source} page")
            soup = BeautifulSoup(result.html, "html.parser")
            abstract_content = extract_abstract(source, soup)
            category_tags = soup.find_all("meta", attrs={"name": "dc.subject"})
            categories = [tag["content"] for tag in category_tags] if category_tags else []
            logger.debug(f"[{source}] Extracted {len(categories)} categories")
        else:
            logger.error(f"[{source}] Failed to crawl {source} page: {url}")
            abstract_content = ""
            categories = []
    return abstract_content, categories

def fill_abstracts(source, papers):
    logger.info(f"[{source}] Filling abstracts for {len(papers)} papers from {source}")
    filled_papers = []
    for idx, paper in enumerate(papers, 1):
        url = paper["abs"]
        logger.debug(f"[{source}] Processing paper {idx}/{len(papers)}: {url}")
        abstract_content, categories = asyncio.run(get_metadata_crawler(source, url))
        if abstract_content:
            paper["summary"] = abstract_content
            if categories:
                paper["category"] = categories
            filled_papers.append(paper)
            logger.debug(f"[{source}] Successfully filled abstract for paper {idx}/{len(papers)}")
        else:
            logger.warning(f"[{source}] No abstract content found for paper {idx}/{len(papers)}: {url}")
    logger.info(f"[{source}] Successfully filled {len(filled_papers)} out of {len(papers)} papers from {source}")
    return filled_papers
############# Not Finished yet

def process_source(extractor, source: str, categories: str, output_base: str, output_dir: str = "data", cache_dir: str = "data/cache") -> dict:
    """
    Process a single RSS source.
    
    Args:
        source: Source type ('arxiv', etc.)
        categories: Categories to fetch
        output_base: Base name for output file (without extension)
        output_dir: Directory for output files
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"="*60)
    logger.info(f"Processing source: {source}")
    logger.info(f"Categories: {categories}")
    logger.info(f"="*60)
    
    # Create source-specific output file
    output_file = os.path.join(output_dir, f"{output_base}_{source}.jsonl")
    logger.info(f"Output file: {output_file}")
    
    fetcher = RSSFetcher(source=source, categories=categories, cache_dir=cache_dir)
    
    # Load cache to check for updates
    cached_ids = fetcher.load_cache()
    
    # Fetch new papers from RSS
    papers = fetcher.fetch()
    
    # Filter out papers that are already in cache or output file
    new_papers = [p for p in papers if p['id'] not in cached_ids]
    
    result = {
        'source': source,
        'total_papers': len(papers),
        'new_papers': len(new_papers),
        'new_papers_with_abs': 0,
        'output_file': output_file
    }
    
    if new_papers:
        logger.info(f"[{source}] Found {len(new_papers)} new papers (out of {len(papers)} total)")
        
        # Extract abstracts using the fallback chain
        if source != 'arxiv':
            new_papers = extractor.extract_abstracts(new_papers, source=source)
        
        # Update count after extraction
        result['new_papers_with_abs'] = len([p for p in new_papers if p.get('summary')])            
        
        # Append new papers to the output file
        append_mode = os.path.exists(output_file)
        fetcher.save_to_jsonl(new_papers, output_file, append=append_mode)
    else:
        logger.info(f"[{source}] No new papers found (checked {len(papers)} papers)")
        if not os.path.exists(output_file):
            fetcher.save_to_jsonl(new_papers, output_file)
            logger.info(f"[{source}] Created empty output file")
        else:
            logger.info(f"[{source}] Output file already exists, skipping save")
        
    # Update cache with current paper IDs
    all_ids = set(p['id'] for p in papers)
    fetcher.save_cache(all_ids)
    
    logger.info(f"[{source}] Processing completed")
    return result


def rss_fetcher_main(output='0000-00-00', output_dir='data', sources='arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms+nphys+natrevphys+lsa+natmachintell,science:science+sciadv,optica:optica,aps:prl+prx+rmp', ):

    # Parse comma-separated sources
    sources_categories = [s.strip() for s in sources.split(',')]
    sources, categories = zip(*[s.split(':') for s in sources_categories])
    Path(output_dir).mkdir(exist_ok=True)
    cache_dir = os.path.join(output_dir, 'cache')
    
    # Validate all sources
    invalid_sources = [s for s in sources if s not in RSSFetcher.SUPPORTED_SOURCES]
    if invalid_sources:
        logger.error(f"Invalid sources: {invalid_sources}. Supported: {RSSFetcher.SUPPORTED_SOURCES}")
        return 1
    
    logger.info("="*60)
    logger.info("Starting Multi-Source RSS Fetcher")
    logger.info(f"Sources: {sources}")
    logger.info(f"Categories: {categories}")
    logger.info(f"Output base: {output}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Cache directory: {cache_dir}")
    logger.info("="*60)
    
    # Process each source
    extractor = AbstractExtractor()
    results = []
    for source, category in zip(sources, categories):
        try:
            result = process_source(extractor, source, category, output, output_dir, cache_dir=cache_dir)
            results.append(result)
        except Exception as e:
            logger.error(f"[{source}] Failed to process: {e}", exc_info=True)
            results.append({
                'source': source,
                'error': str(e)
            })
    
    update_file = os.path.join(cache_dir, f"update.json")
    try:
        cache_data = {
            'message': results,
            'last_updated': datetime.now().isoformat()
        }
        with open( update_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved papers to {update_file}")
    except IOError as e:
        logger.error(f"Failed to save papers to {update_file}: {e}")
    
    # Summary
    logger.info("="*60)
    logger.info("Processing Summary")
    logger.info("="*60)
    
    total_new = 0
    total_new_with_abs = 0
    for result in results:
        if 'error' in result:
            logger.info(f"[{result['source']}] Failed: {result['error']}")
        else:
            logger.info(f"[{result['source']}] {result['new_papers_with_abs']} new papers with abstract / {result['new_papers']} new papers / {result['total_papers']} total")
            total_new += result['new_papers']
            total_new_with_abs += result['new_papers_with_abs']
    
    logger.info(f"Total new papers across {len(sources)} sources(s): {total_new_with_abs} (with abstracts) / {total_new} (total)")
    logger.info("="*60)
    
    return 0


if __name__ == '__main__':
    rss_fetcher_main()
