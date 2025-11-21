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


# API Endpoints
@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Get all favorites"""
    favorites = load_favorites()
    return jsonify(favorites)


@app.route('/api/favorites', methods=['POST'])
def update_favorites():
    """Update favorites"""
    data = request.json
    if save_favorites(data):
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
    print(f"Server running at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=False)
