#!/usr/bin/env python3
"""
Simple API server for handling favorites persistence.
Stores favorites data in data/cache/favorites.json
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path

app = Flask(__name__, static_folder='.')
CORS(app)

# Path to favorites storage
FAVORITES_FILE = Path('data/cache/favorites.json')
FOLDERS_FILE = Path('data/cache/favorites_folders.json')
FAVORITES_PAPERS_CACHE = Path('data/cache/favorites_papers.json')

# Ensure cache directory exists
FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_favorites():
    """Load favorites from JSON file"""
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading favorites: {e}")
            return {}
    return {}


def save_favorites(favorites):
    """Save favorites to JSON file"""
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False


def load_folders():
    """Load favorites folders from JSON file"""
    if FOLDERS_FILE.exists():
        try:
            with open(FOLDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading folders: {e}")
            return ['Default']
    return ['Default']


def save_folders(folders):
    """Save favorites folders to JSON file"""
    try:
        with open(FOLDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(folders, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving folders: {e}")
        return False


def load_favorites_papers_cache():
    """Load cached favorited papers from JSON file"""
    if FAVORITES_PAPERS_CACHE.exists():
        try:
            with open(FAVORITES_PAPERS_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading favorites papers cache: {e}")
            return []
    return []


def save_favorites_papers_cache(papers):
    """Save favorited papers to cache file"""
    try:
        with open(FAVORITES_PAPERS_CACHE, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites papers cache: {e}")
        return False


def update_favorites_papers_cache(paper_ids_to_add=None, paper_ids_to_remove=None):
    """
    Update the favorites papers cache.
    This is called when favorites are modified to keep the cache in sync.
    Tries to load AI enhanced versions first, then falls back to original files.
    
    Args:
        paper_ids_to_add: List of paper IDs to fetch and add to cache
        paper_ids_to_remove: List of paper IDs to remove from cache
    """
    cached_papers = load_favorites_papers_cache()
    
    # Create a mapping by paper ID for quick lookup
    papers_map = {paper['id']: paper for paper in cached_papers}
    
    # Remove papers
    if paper_ids_to_remove:
        for paper_id in paper_ids_to_remove:
            papers_map.pop(paper_id, None)
    
    # Add new papers by searching through data files
    if paper_ids_to_add:
        data_dir = Path('data')
        existing_ids = set(papers_map.keys())
        ids_to_find = set(paper_ids_to_add) - existing_ids
        
        if ids_to_find:
            # Get list of available languages (Chinese, English)
            languages = ['Chinese', 'English']
            
            # Build a mapping of date -> source -> files for efficient lookup
            date_source_files = {}
            for jsonl_file in data_dir.glob('*.jsonl'):
                if '_AI_enhanced_' in jsonl_file.name:
                    continue
                
                # Extract date and source from filename
                date_match = jsonl_file.name.split('_')
                if len(date_match) >= 2:
                    file_date = date_match[0]  # e.g., "2025-11-05"
                    source = jsonl_file.stem.split('_')[-1]  # e.g., "nature"
                    
                    if file_date not in date_source_files:
                        date_source_files[file_date] = {}
                    date_source_files[file_date][source] = jsonl_file
            
            # Search through original files to find papers and their metadata
            for file_path in sorted(data_dir.glob('*.jsonl')):
                if '_AI_enhanced_' in file_path.name or not ids_to_find:
                    continue
                
                # Extract date and source for this file
                date_match = file_path.name.split('_')
                if len(date_match) < 2:
                    continue
                
                file_date = date_match[0]
                source = file_path.stem.split('_')[-1]
                
                try:
                    # First, try to load from AI enhanced version
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
                                            print(f"Loaded {paper['id']} from AI enhanced ({lang}): {ai_enhanced_path.name}")
                                            
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
                                        print(f"Loaded {paper['id']} from original: {file_path.name}")
                                        
                                        if not ids_to_find:
                                            break
                
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    # Save updated cache
    updated_papers = list(papers_map.values())
    save_favorites_papers_cache(updated_papers)
    return updated_papers


# API Endpoints
@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Get all favorites"""
    favorites = load_favorites()
    return jsonify(favorites)


@app.route('/api/favorites', methods=['POST'])
def update_favorites():
    """Update favorites and sync the papers cache"""
    data = request.json
    old_favorites = load_favorites()
    
    # Determine which papers were added or removed
    old_ids = set()
    for folder_ids in old_favorites.values():
        old_ids.update(folder_ids)
    
    new_ids = set()
    for folder_ids in data.values():
        new_ids.update(folder_ids)
    
    added_ids = list(new_ids - old_ids)
    removed_ids = list(old_ids - new_ids)
    
    # Update favorites list
    if save_favorites(data):
        # Update the papers cache
        update_favorites_papers_cache(paper_ids_to_add=added_ids, paper_ids_to_remove=removed_ids)
        return jsonify({'status': 'success', 'message': 'Favorites saved'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save favorites'}), 500


@app.route('/api/favorites/ids', methods=['GET'])
def get_favorite_ids():
    """Get all favorite paper IDs (flattened from all folders)"""
    favorites = load_favorites()
    all_ids = []
    for folder_ids in favorites.values():
        all_ids.extend(folder_ids)
    # Remove duplicates
    unique_ids = list(set(all_ids))
    return jsonify(unique_ids)


@app.route('/api/favorites/folders', methods=['GET'])
def get_folders():
    """Get all folders"""
    folders = load_folders()
    return jsonify(folders)


@app.route('/api/favorites/folders', methods=['POST'])
def update_folders():
    """Update folders"""
    data = request.json
    if isinstance(data, list):
        if save_folders(data):
            return jsonify({'status': 'success', 'message': 'Folders saved'})
    return jsonify({'status': 'error', 'message': 'Invalid data or save failed'}), 400


@app.route('/api/favorites/papers', methods=['GET'])
def get_favorites_papers():
    """Get all cached favorited papers"""
    papers = load_favorites_papers_cache()
    return jsonify(papers)


@app.route('/api/favorites/papers/refresh', methods=['POST'])
def refresh_favorites_papers():
    """Rebuild the entire favorites papers cache from current favorites list"""
    favorites = load_favorites()
    all_ids = []
    for folder_ids in favorites.values():
        all_ids.extend(folder_ids)
    unique_ids = list(set(all_ids))
    
    # Rebuild cache with all current favorite IDs
    updated_papers = update_favorites_papers_cache(paper_ids_to_add=unique_ids, paper_ids_to_remove=[])
    return jsonify({
        'status': 'success',
        'message': f'Refreshed cache with {len(updated_papers)} papers'
    })


# Serve static files
@app.route('/')
def serve_index():
    """Serve index.html"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)


if __name__ == '__main__':

    import argparse
    
    parser = argparse.ArgumentParser(description='API server for favorites persistence')
    parser.add_argument('--host', type=str, default='127.0.0.1:8000', help='Host to bind to (default: 127.0.0.1:8000)')
    args = parser.parse_args()
    host = args.host.split(':')[0]
    port = int(args.host.split(':')[1])

    print("Starting API server...")
    print(f"Favorites file: {FAVORITES_FILE.absolute()}")
    print(f"Folders file: {FOLDERS_FILE.absolute()}")
    print(f"Favorites papers cache: {FAVORITES_PAPERS_CACHE.absolute()}")
    print(f"Server running at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=False)
