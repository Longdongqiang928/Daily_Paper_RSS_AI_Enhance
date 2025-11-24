import numpy as np
from datetime import datetime
from pyzotero import zotero
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
import pickle
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger

logger = get_logger(__name__)

class ZoteroRecommender:
    def __init__(self, embedding_model: str, use_cache: bool = False, cache_dir: str = 'data/cache'):
        """
        Initialize Zotero recommender with OpenAI-compatible embedding model.
        
        Args:
            embedding_model: Model name (e.g., 'text-embedding-3-small')
            use_cache: If True, try to load corpus from cache instead of fetching from Zotero
            cache_dir: Directory to store cache files
        """
        self.embedding_model_name = embedding_model
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.environ.get('NEWAPI_KEY_AD'), base_url=os.environ.get('NEWAPI_BASE_URL'))
        
        self.collections = set()
        self.corpus = self.get_zotero_corpus()
        
        logger.info(f"Initialized ZoteroRecommender with model: {embedding_model}")
        logger.info(f"Using API base URL: {os.environ.get('NEWAPI_BASE_URL')}")
        logger.info(f"Cache enabled: {use_cache}")
    
    def get_zotero_corpus(self) -> List[Dict]:
        """
        Get Zotero corpus, either from cache or by fetching from Zotero API.
        Cache is used only if use_cache=True and cache exists and is recent (< 24 hours old).
        """
        cache_file = self.cache_dir / 'zotero_corpus.pkl'
        cache_timestamp_file = self.cache_dir / 'zotero_corpus_timestamp.txt'
        
        # Check if we should use cache
        if self.use_cache and cache_file.exists() and cache_timestamp_file.exists():
            try:
                # Read cache timestamp
                with open(cache_timestamp_file, 'r') as f:
                    cache_time_str = f.read().strip()
                cache_time = datetime.fromisoformat(cache_time_str)
                
                # Check if cache is less than 24 hours old
                if datetime.now() - cache_time < timedelta(hours=24):
                    logger.info("Loading Zotero corpus from cache")
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    self.collections = cached_data['collections']
                    corpus = cached_data['corpus']
                    
                    logger.info(f"Loaded {len(corpus)} papers from cache (cached at {cache_time})")
                    logger.info(f"Total collections: {len(self.collections)}")
                    return corpus
                else:
                    logger.info(f"Cache is older than 24 hours (cached at {cache_time}), fetching fresh data")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}, fetching fresh data")
        
        # Fetch from Zotero API
        logger.info("Fetching Zotero corpus from API")
        zot = zotero.Zotero(os.environ.get('ZOTERO_ID'), 'user', os.environ.get('ZOTERO_KEY_AD'))
        collections = zot.everything(zot.collections())
        collections = {c['key']: c for c in collections}
        
        corpus = zot.everything(zot.items(itemType='conferencePaper || journalArticle || preprint'))
        corpus = [c for c in corpus if c['data']['abstractNote'] != '']
        logger.info(f"Found {len(corpus)} papers with abstracts")
        
        def get_collection_path(col_key: str) -> str:
            if p := collections[col_key]['data']['parentCollection']:
                return get_collection_path(p) + '/' + collections[col_key]['data']['name']
            else:
                return collections[col_key]['data']['name']
        
        for c in corpus:
            paths = [get_collection_path(col) for col in c['data']['collections']]
            c['paths'] = paths
            self.collections.update(paths)
        
        logger.info(f"Finished fetching Zotero corpus. Total collections found: {len(self.collections)}")
        
        # Save to cache if caching is enabled
        if self.use_cache:
            try:
                cache_data = {
                    'corpus': corpus,
                    'collections': self.collections
                }
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                
                with open(cache_timestamp_file, 'w') as f:
                    f.write(datetime.now().isoformat())
                
                logger.info(f"Saved Zotero corpus to cache: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")
        
        return corpus
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings from OpenAI-compatible API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of embeddings
        """
        logger.debug(f"Getting embeddings for {len(texts)} texts")
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.embedding_model_name
            )
            embeddings = np.array([item.embedding for item in response.data])
            logger.debug(f"Got embeddings with shape: {embeddings.shape}")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            raise
    
    def compute_similarity(self, query_embeddings: np.ndarray, corpus_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and corpus embeddings.
        
        Args:
            query_embeddings: Query embeddings (n_queries, dim)
            corpus_embeddings: Corpus embeddings (n_corpus, dim)
            
        Returns:
            Similarity matrix (n_queries, n_corpus)
        """
        # Normalize embeddings
        query_norm = query_embeddings / np.linalg.norm(query_embeddings, axis=1, keepdims=True)
        corpus_norm = corpus_embeddings / np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarity = np.dot(query_norm, corpus_norm.T)
        return similarity
    
    def rerank_paper(self, candidates: List[Dict], source: str) -> List[Dict]:
        logger.info(f"[{source}] Starting paper re-ranking process")
        
        for c in candidates:
            if 'score' not in c:
                c['score'] = {}
        
        logger.info(f"[{source}] Processing {len(candidates)} candidates against {len(self.collections)} collections")
        idx_collection = 1
        for collection in self.collections:
            if candidates and collection in candidates[0]['score']:
                logger.info(f'[{source}] Collection {collection} ({idx_collection}/{len(self.collections)}) already processed')
                idx_collection += 1
                continue
            
            collection_corpus = [p for p in self.corpus if collection in p.get('paths', [])]
            if collection_corpus:
                collection_corpus = sorted(
                    collection_corpus,
                    key=lambda x: datetime.strptime(x['data']['dateAdded'], '%Y-%m-%dT%H:%M:%SZ'),
                    reverse=True
                )
                time_decay_weight = 1 / (1 + np.log10(np.arange(len(collection_corpus)) + 1))
                time_decay_weight = time_decay_weight / time_decay_weight.sum()
                
                # Get embeddings using OpenAI-compatible API
                corpus_texts = [paper['data']['abstractNote'] for paper in collection_corpus]
                candidate_texts = [paper['summary'] for paper in candidates]
                
                logger.debug(f"[{source}] Getting embeddings for collection: {collection}")
                corpus_embeddings = self.get_embeddings(corpus_texts)
                candidate_embeddings = self.get_embeddings(candidate_texts)
                
                # Compute similarity
                sim = self.compute_similarity(candidate_embeddings, corpus_embeddings)
                scores = (sim * time_decay_weight).sum(axis=1) * 10
                
                for s, c in zip(scores, candidates):
                    c['score'][collection] = float(s)
                
                logger.info(f'[{source}] Collection {collection} ({idx_collection}/{len(self.collections)}) done')
                idx_collection += 1
        
        for c in candidates:
            if c['score']:
                c['score'] = dict(sorted(c['score'].items(), key=lambda item: item[1], reverse=True))
                filtered_collections = [k for k, v in c['score'].items() if v > 4]
                if filtered_collections:
                    while 'max' in filtered_collections:
                        filtered_collections.remove('max')
                    c['collection'] = filtered_collections
                else:
                    max_score_collections = list(max(c['score'].items(), key=lambda x: x[1]))
                    while 'max' in max_score_collections:
                        max_score_collections.remove('max')
                    c['collection'] = [max_score_collections[0]]
                c['score']['max'] = max(c['score'].values())
        
        candidates = sorted(candidates, key=lambda x: x['score'].get('max', 0), reverse=True)
        logger.info(f"[{source}] Completed re-ranking, top score: {candidates[0]['score'].get('max', 0) if candidates else 0}")
        
        return candidates


def process_multi_source_files(data_pattern: str, recommender: ZoteroRecommender, output_dir: str = "data") -> List[str]:
    """
    Process multiple JSONL files from different sources.
    
    Args:
        data_pattern: Pattern to match files (e.g., '2025-10-31')
        recommender: ZoteroRecommender instance
        output_dir: Directory containing the files
        
    Returns:
        List of processed file paths
    """

    # Find all matching files with pattern
    data_path = Path(output_dir)
    files = list(data_path.glob(f"{data_pattern}_*.jsonl"))
    # Exclude already enhanced files
    files = [str(f) for f in files if '_AI_enhanced_' not in f.name]
    
    if not files:
        logger.warning(f"No files found matching pattern: {data_pattern}")
        return []
    
    logger.info(f"Found {len(files)} files to process: {files}")
    processed_files = []
    
    for file_path in files:
        source = Path(file_path).stem.split('_')[-1] if '_' in Path(file_path).stem else 'unknown'
        try:
            logger.info(f"="*60)
            logger.info(f"Processing file: {file_path}")
            logger.info(f"="*60)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                candidates = [json.loads(line) for line in f if line.strip()]
            
            if not candidates:
                logger.warning(f"No candidates found in {file_path}")
                continue
            
            # Detect source from filename or paper data
            logger.info(f"Detected source: {source}, papers: {len(candidates)}")
            
            # Re-rank papers
            candidates = recommender.rerank_paper(candidates, source)
            
            # Save back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                for c in candidates:
                    f.write(json.dumps(c, ensure_ascii=False) + '\n')
            
            logger.info(f"[{source}] Successfully processed {file_path}")
            processed_files.append(file_path)
            
        except Exception as e:
            logger.error(f"[{source}] Failed to process {file_path}: {e}", exc_info=True)
    
    return processed_files


def zotero_recommender_main(data='0000-00-00', data_dir="data", embedding_model='qwen3-embedding-8b', use_cache=False):
    """
    Main entry point for Zotero recommender.
    
    Args:
        data: Date pattern to match files
        data_dir: Directory containing the files
        embedding_model: Embedding model name
        use_cache: If True, use cached Zotero corpus (for weekly batch processing)
    """
    logger.info("="*60)
    logger.info("Starting Zotero Recommender (Multi-Source, OpenAI-Compatible)")
    logger.info(f"Data pattern: {data}")
    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"API base URL: {os.environ.get('NEWAPI_BASE_URL')}")
    logger.info(f"Use cache: {use_cache}")
    logger.info("="*60)
    
    recommender = ZoteroRecommender(embedding_model, use_cache=use_cache)
    
    # Process multiple source files
    processed_files = process_multi_source_files(data, recommender, data_dir)
    
    logger.info("="*60)
    logger.info("Processing Summary")
    logger.info(f"Successfully processed {len(processed_files)} file(s)")
    for file_path in processed_files:
        logger.info(f"  - {file_path}")
    logger.info("="*60)


if __name__ == '__main__':
    zotero_recommender_main()
