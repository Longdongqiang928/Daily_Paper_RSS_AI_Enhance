#!/usr/bin/env python3
"""
Utility script to refresh the favorites papers cache.
This script rebuilds the favorites_papers.json cache from the current favorites list.
"""

import json
from pathlib import Path


def refresh_favorites_cache():
    """Rebuild the favorites papers cache from current favorites list"""
    
    # Paths
    favorites_file = Path('data/cache/favorites.json')
    cache_file = Path('data/cache/favorites_papers.json')
    data_dir = Path('data')
    
    # Ensure cache directory exists
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load favorites list
    if not favorites_file.exists():
        print(f"No favorites file found at {favorites_file}")
        print("Creating empty cache...")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return
    
    with open(favorites_file, 'r', encoding='utf-8') as f:
        favorites = json.load(f)
    
    # Collect all favorite paper IDs
    all_ids = set()
    for folder_ids in favorites.values():
        all_ids.update(folder_ids)
    
    if not all_ids:
        print("No favorite papers found")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return
    
    print(f"Found {len(all_ids)} unique favorite paper IDs")
    print(f"Searching for papers in {data_dir}...")
    
    # Search through all JSONL files to find the papers
    # Prefer AI enhanced versions over original files
    papers_map = {}
    ids_to_find = set(all_ids)
    languages = ['Chinese', 'English']
    
    jsonl_files = sorted(data_dir.glob('*.jsonl'))
    original_files = [f for f in jsonl_files if '_AI_enhanced_' not in f.name]
    
    for file_path in original_files:
        if not ids_to_find:
            break
        
        # Extract date and source from filename
        date_match = file_path.name.split('_')
        if len(date_match) < 2:
            continue
        
        file_date = date_match[0]  # e.g., "2025-11-05"
        source = file_path.stem.split('_')[-1]  # e.g., "nature"
        
        try:
            # First, try to load from AI enhanced versions
            paper_loaded = False
            for lang in languages:
                ai_enhanced_path = data_dir / f"{file_date}_{source}_AI_enhanced_{lang}.jsonl"
                if ai_enhanced_path.exists():
                    with open(ai_enhanced_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                paper = json.loads(line)
                                if paper['id'] in ids_to_find:
                                    # Add metadata
                                    paper['fileDate'] = file_date
                                    paper['source'] = source
                                    papers_map[paper['id']] = paper
                                    ids_to_find.remove(paper['id'])
                                    paper_loaded = True
                                    print(f"  Found: {paper['id']} in {ai_enhanced_path.name} (AI enhanced - {lang})")
                                    
                                    if not ids_to_find:
                                        break
                    if paper_loaded or not ids_to_find:
                        break
            
            # If not found in AI enhanced versions, try original file
            if not paper_loaded and ids_to_find:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            paper = json.loads(line)
                            if paper['id'] in ids_to_find:
                                # Add metadata
                                paper['fileDate'] = file_date
                                paper['source'] = source
                                papers_map[paper['id']] = paper
                                ids_to_find.remove(paper['id'])
                                print(f"  Found: {paper['id']} in {file_path.name} (original)")
                                
                                if not ids_to_find:
                                    break
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
    
    # Save cache
    cached_papers = list(papers_map.values())
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cached_papers, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Cache refresh complete!")
    print(f"  Favorite IDs: {len(all_ids)}")
    print(f"  Papers found: {len(cached_papers)}")
    print(f"  Papers not found: {len(ids_to_find)}")
    if ids_to_find:
        print(f"  Missing IDs: {list(ids_to_find)[:10]}{'...' if len(ids_to_find) > 10 else ''}")
    print(f"  Cache saved to: {cache_file.absolute()}")
    print(f"{'='*60}")


if __name__ == '__main__':
    refresh_favorites_cache()
