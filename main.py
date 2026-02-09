import argparse
from datetime import datetime, timedelta
import schedule
import time
import os
import sys
from dotenv import load_dotenv
from fetcher.rss_fetcher import rss_fetcher_main
from ai.zotero_recommender import zotero_recommender_main
from ai.enhance import enhance_main
from ai.translate import translate_main
from md.convert_to_md import convert_to_md_main

# Load environment variables
load_dotenv()

class Config:
    def __init__(self):
        self.sources = os.getenv('RSS_SOURCES', 'arxiv:physics+quant-ph+cond-mat+nlin,science:science+sciadv,optica:optica,aps:prl+prx+rmp,nature:nature+nphoton+ncomms+nphys+natrevphys+lsa+natmachintell')
        self.output_dir = os.getenv('OUTPUT_DIR', 'data')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', "qwen3-embedding-8b-f16")
        self.model_name = os.getenv('MODEL_NAME', "qwen3-30b-a3b-instruct-2507")
        self.max_workers = int(os.getenv('MAX_WORKERS', 1))
        self.language = os.getenv('OUTPUT_LANGUAGE', "Chinese")

def validate_date(date_str):
    """Validate date string format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")

def parse_args():
    parser = argparse.ArgumentParser(description='Daily Paper RSS AI Enhance - Academic Paper Processor')
    
    parser.add_argument(
        '--immediate', 
        action='store_true', 
        help='Execute the task immediately instead of waiting for the scheduled time'
    )
    
    parser.add_argument(
        '--mode', 
        choices=['daily', 'weekly', 'full'], 
        default='weekly',
        help='Task mode for immediate execution: "daily", "weekly" (last week), or "full" (all history)'
    )
    
    parser.add_argument(
        '--date', 
        type=validate_date,
        help='Specify a date for processing (format: YYYY-MM-DD). If not specified, defaults to today for daily task.'
    )
    
    return parser.parse_args()

def main(config, date=None):
    """Daily update: fetch new papers and process them (no cache)"""
    if date is None:
        current_time = datetime.now()
        date = current_time.strftime("%Y-%m-%d")
    
    print(f"Starting daily task for date: {date}")
    rss_fetcher_main(date, config.output_dir, config.sources)
    zotero_recommender_main(date, config.output_dir, config.embedding_model, use_cache=False)
    enhance_main(date, config.output_dir, config.model_name, config.language, config.max_workers)
    translate_main(date, config.output_dir, config.model_name, config.language)
    
    # Convert to markdown if not already exists
    convert_to_md_main(date, config.output_dir, config.language)

    # Write list of files in data folder to file-list.txt
    data_dir = config.output_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        files = list(set([str(f) for f in files if '_AI_enhanced_' not in f]))
        with open('data/cache/file-list.txt', 'w', encoding='utf-8') as f:
            for file in files:
                f.write(file + '\n')

def main_week_check(config):
    """Weekly check: re-process files from the last week using cached Zotero library"""
    print(f"Starting weekly task (last week)...")
    data_dir = config.output_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        all_dates = list(set([str(f)[0:10] for f in files if '_AI_enhanced_' not in f]))
        
        # Filter for dates within the last 7 days
        one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        files = [d for d in all_dates if d >= one_week_ago]
        
        # Sort files in chronological order (oldest to newest)
        files.sort()
        print(f"Processing {len(files)} dates from the last week: {files}")
        
        # Process filtered files with cache enabled (only fetch Zotero once)
        for output in files:
            zotero_recommender_main(output, config.output_dir, config.embedding_model, use_cache=True)
            enhance_main(output, config.output_dir, config.model_name, config.language, config.max_workers)
            translate_main(output, config.output_dir, config.model_name, config.language)
            
            # Convert to markdown if not already exists
            convert_to_md_main(output, config.output_dir, config.language)

        # Write list of files in data folder to file-list.txt
        data_dir = config.output_dir
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
            files = list(set([str(f) for f in files if '_AI_enhanced_' not in f]))
            with open('data/cache/file-list.txt', 'w', encoding='utf-8') as f:
                for file in files:
                    f.write(file + '\n')

def main_full_check(config):
    """Full check: re-process all existing files using cached Zotero library"""
    print(f"Starting full historical task...")
    data_dir = config.output_dir
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        files = list(set([str(f)[0:10] for f in files if '_AI_enhanced_' not in f]))
        
        # Sort files in chronological order (oldest to newest)
        files.sort()
        print(f"Processing all {len(files)} dates in history: {files}")
        
        # Process all files with cache enabled (only fetch Zotero once)
        for output in files:
            zotero_recommender_main(output, config.output_dir, config.embedding_model, use_cache=True)
            enhance_main(output, config.output_dir, config.model_name, config.language, config.max_workers)
            translate_main(output, config.output_dir, config.model_name, config.language)
            
            # Convert to markdown if not already exists
            convert_to_md_main(output, config.output_dir, config.language)

        # Write list of files in data folder to file-list.txt
        data_dir = config.output_dir
        if os.path.exists(data_dir) and os.path.isdir(data_dir):
            files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
            files = list(set([str(f) for f in files if '_AI_enhanced_' not in f]))
            with open('data/cache/file-list.txt', 'w', encoding='utf-8') as f:
                for file in files:
                    f.write(file + '\n')


if __name__ == '__main__':
    args = parse_args()
    config = Config()
    
    if args.immediate:
        print(f"Running immediate task in {args.mode} mode...")
        if args.mode == 'daily':
            main(config, date=args.date)
        elif args.mode == 'weekly':
            main_week_check(config)
        elif args.mode == 'full':
            main_full_check(config)
        print("Immediate task completed.")
    else:
        print("Scheduling tasks: Daily at 08:00, Weekly on Sunday at 10:00")
        schedule.every().day.at("08:00").do(main, config=config).tag('daily-tasks')
        schedule.every().sunday.at("10:00").do(main_week_check, config=config).tag('weekly-tasks')
        
        while True:
            schedule.run_pending()
            time.sleep(60)
