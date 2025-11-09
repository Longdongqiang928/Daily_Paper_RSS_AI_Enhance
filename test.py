import argparse
from datetime import datetime
import schedule
import time
import os
from fetcher.rss_fetcher import rss_fetcher_main
from ai.zotero_recommender import zotero_recommender_main
from ai.enhance import enhance_main

def parse_args():
    parser = argparse.ArgumentParser(description='Generic RSS fetcher for academic papers')
    parser.add_argument(
        '--sources', 
        type=str, 
        default='arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms+nphys+natrevphys+lsa+natmachintell',
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
        default="qwen3-embedding-8b",
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

def main(args):
    date = "0000-00-00"
    rss_fetcher_main(date, args.output_dir, args.sources)
    zotero_recommender_main(date, args.output_dir, args.embedding_model)
    enhance_main(date, args.output_dir, args.model_name, args.language, args.max_workers)

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
        print(files)
        for output in files:
            zotero_recommender_main(output, args.output_dir, args.embedding_model)
            enhance_main(output, args.output_dir, args.model_name, args.language, args.max_workers)

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
    main(args)
    # main_week_check(args)
