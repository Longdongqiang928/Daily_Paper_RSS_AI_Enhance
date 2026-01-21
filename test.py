import argparse
import os
from fetcher.rss_fetcher import rss_fetcher_main
from ai.zotero_recommender import zotero_recommender_main
from ai.enhance import enhance_main
from ai.translate import translate_main
from md.convert_to_md import convert_to_md_main

def parse_args():
    parser = argparse.ArgumentParser(description='Generic RSS fetcher for academic papers')
    parser.add_argument(
        '--sources', 
        type=str, 
        # default='arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms+nphys+natrevphys+lsa+natmachintell,science:science+sciadv,optica:optica,aps:prl+prx+rmp',
        default='arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms+nphys+natrevphys+lsa+natmachintell,science:science+sciadv,optica:optica,aps:prl+prx+rmp',
        help='Comma-separated list of RSS sources:categories (e.g., arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton,science:science+sciadv)'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='data',
        help='Directory for output files (default: data)'
    )
    parser.add_argument(
        "--embedding_model", 
        type=str, 
        default="qwen3-embedding-8b-f16",
        help="OpenAI-compatible embedding model name"
    )
    parser.add_argument(
        "--model_name", 
        type=str, 
        help="LLM Model Name", 
        default="qwen3-30b-a3b-instruct-2507"
    )
    parser.add_argument(
        "--max_workers", 
        type=int, 
        default=1, 
        help="Maximum number of parallel workers"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default="Chinese", 
        help="Language for the output"
    )

    return parser.parse_args()

from datetime import datetime

def main(args):
    # current_time = datetime.now()
    # date = current_time.strftime("%Y-%m-%d")
    date = '0000-00-00'
    rss_fetcher_main(date, args.output_dir, args.sources)
    zotero_recommender_main(date, args.output_dir, args.embedding_model, use_cache=False)
    enhance_main(date, args.output_dir, args.model_name, args.language, args.max_workers)
    translate_main(date, args.output_dir, args.model_name, args.language)
    
    # Convert to markdown if not already exists
    convert_to_md_main(date, args.output_dir, args.language)

    # Write list of files in data folder to file-list.txt
    data_dir = args.output_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        files = list(set([str(f) for f in files if '_AI_enhanced_' not in f]))
        with open('data/cache/file-list.txt', 'w', encoding='utf-8') as f:
            for file in files:
                f.write(file + '\n')

def main_week_check(args):
    from pathlib import Path

    data_dir = args.output_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        files = list(set([str(f)[0:10] for f in files if '_AI_enhanced_' not in f]))
        
        # Sort files in chronological order (oldest to newest)
        files.sort()
        print(f"Processing {len(files)} dates in chronological order: {files}")
        
        for output in files:
            zotero_recommender_main(output, args.output_dir, args.embedding_model, use_cache=True)
            enhance_main(output, args.output_dir, args.model_name, args.language, args.max_workers)
            translate_main(output, args.output_dir, args.model_name, args.language)
            
            # Convert to markdown if not already exists
            convert_to_md_main(output, args.output_dir, args.language)

        # Write list of files in data folder to file-list.txt
        data_dir = args.output_dir
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
            files = list(set([str(f) for f in files if '_AI_enhanced_' not in f]))
            with open('data/cache/file-list.txt', 'w', encoding='utf-8') as f:
                for file in files:
                    f.write(file + '\n')


if __name__ == '__main__':
    args = parse_args()
    # main(args)
    main_week_check(args)
