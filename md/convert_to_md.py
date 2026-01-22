"""Convert AI-enhanced JSONL files to Markdown format.

This module provides functionality to convert AI-enhanced paper data (JSONL)
into well-formatted Markdown files for easy reading and archival.
"""

import json
import os
import sys
from itertools import count
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger

logger = get_logger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent
OUTPUT_DIR_NAME = "md_files"


def load_template() -> str:
    """Load the markdown template for papers."""
    template_path = TEMPLATE_DIR / "template.md"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        raise


def load_jsonl_data(file_path: str) -> List[dict]:
    """Load data from a JSONL file."""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def get_md_output_path(date: str, data_dir: str = "data") -> Path:
    """Get the output path for the markdown file.
    
    Args:
        date: Date string in format 'YYYY-MM-DD'
        data_dir: Base data directory
        
    Returns:
        Path to the output markdown file
    """
    output_dir = Path(data_dir) / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{date}_papers.md"


def md_file_exists(date: str, data_dir: str = "data") -> bool:
    """Check if the markdown file for a given date already exists.
    
    Args:
        date: Date string in format 'YYYY-MM-DD'
        data_dir: Base data directory
        
    Returns:
        True if the file exists, False otherwise
    """
    output_path = get_md_output_path(date, data_dir)
    return output_path.exists()


def convert_papers_to_markdown(
    papers: List[dict],
    date: str,
    template: str
) -> str:
    """Convert a list of papers to markdown format.
    
    Args:
        papers: List of paper dictionaries with AI enhancement
        date: Date string for the header
        template: Markdown template string
        
    Returns:
        Complete markdown string
    """
    # Group papers by journal/source
    journals = {}
    for paper in papers:
        journal = paper.get('journal', 'Unknown')
        if journal not in journals:
            journals[journal] = []
        journals[journal].append(paper)
    
    # Sort journals alphabetically
    sorted_journals = sorted(journals.keys())
    
    # Generate table of contents
    markdown = f"# Daily Papers - {date}\n\n"
    markdown += "<div id='toc'></div>\n\n"
    markdown += "## Table of Contents\n\n"
    
    
    total_papers = 0
    for journal in sorted_journals:
        paper_count = len(journals[journal])
        total_papers += paper_count
        # Create anchor-safe ID
        anchor = journal.replace(' ', '-').lower()
        markdown += f"- [{journal}](#{anchor}) [{paper_count} papers]\n"
    
    markdown += f"\n**Total: {total_papers} papers**\n\n"
    markdown += "---\n\n"
    
    # Generate paper sections by journal
    idx = count(1)
    for journal in sorted_journals:
        anchor = journal.replace(' ', '-').lower()
        markdown += f"<div id='{anchor}'></div>\n\n"
        markdown += f"## {journal} [[Back]](#toc)\n\n"
        
        # Sort papers by score (highest first)
        journal_papers = sorted(
            journals[journal],
            key=lambda x: x.get('score', {}).get('max', 0) if isinstance(x.get('score'), dict) else 0,
            reverse=True
        )
        
        for paper in journal_papers:
            # Safely access AI fields
            ai_data = paper.get('AI', {})
            if not ai_data or not isinstance(ai_data, dict):
                logger.debug(f"Skipping paper '{paper.get('title', 'Unknown')}' - missing AI data")
                continue
            
            # Check required AI fields
            required_fields = ['tldr', 'motivation', 'method', 'result', 'conclusion']
            if not all(field in ai_data for field in required_fields):
                logger.debug(f"Skipping paper '{paper.get('title', 'Unknown')}' - incomplete AI fields")
                continue
            
            # Get score value
            score_data = paper.get('score', {})
            if isinstance(score_data, dict):
                score = score_data.get('max', 0)
            else:
                score = 0
            
            # Get collections
            collections = paper.get('collection', [])
            if isinstance(collections, list):
                collections_str = ', '.join(collections) if collections else 'None'
            else:
                collections_str = str(collections) if collections else 'None'
            
            # Get original summary and translated summary separately
            summary_original = paper.get('summary', 'No summary available.')
            summary_translated = ai_data.get('summary_translated', '')
            
            # Create translated section only if translation exists and differs from original
            if summary_translated and summary_translated != summary_original:
                summary_translated_section = f"\n**Abstract (Translated):** {summary_translated}\n\n"
            else:
                summary_translated_section = "\n"
            
            # Format authors
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                authors_str = ', '.join(authors[:5])  # Limit to first 5 authors
                if len(authors) > 5:
                    authors_str += ' et al.'
            else:
                authors_str = str(authors)
            
            try:
                paper_md = template.format(
                    idx=next(idx),
                    title=paper.get('title', 'Untitled'),
                    url=paper.get('abs', '#'),
                    authors=authors_str,
                    journal=paper.get('journal', 'Unknown'),
                    published=paper.get('published', 'Unknown'),
                    score=f"{score:.1f}" if score else 'N/A',
                    tldr=ai_data.get('tldr', 'N/A'),
                    motivation=ai_data.get('motivation', 'N/A'),
                    method=ai_data.get('method', 'N/A'),
                    result=ai_data.get('result', 'N/A'),
                    conclusion=ai_data.get('conclusion', 'N/A'),
                    summary_original=summary_original,
                    summary_translated_section=summary_translated_section,
                    category=paper.get('category', 'Unknown'),
                    collections=collections_str,
                    pdf=paper.get('pdf', '#'),
                    abs=paper.get('abs', '#')
                )
                markdown += paper_md + "\n"
            except Exception as e:
                logger.warning(f"Failed to format paper '{paper.get('title', 'Unknown')}': {e}")
                continue
    
    return markdown


def convert_date_to_md(
    date: str,
    data_dir: str = "data",
    language: str = "Chinese",
    force: bool = False
) -> Optional[str]:
    """Convert AI-enhanced JSONL files for a specific date to markdown.
    
    Args:
        date: Date string in format 'YYYY-MM-DD'
        data_dir: Base data directory containing JSONL files
        language: Language suffix for AI-enhanced files (e.g., 'Chinese', 'English')
        force: If True, regenerate even if MD file exists
        
    Returns:
        Path to the generated markdown file, or None if skipped/failed
    """
    output_path = get_md_output_path(date, data_dir)
    
    # Check if MD file already exists
    if not force and output_path.exists():
        logger.info(f"MD file already exists for {date}, skipping: {output_path}")
        return None
    
    # Find all AI-enhanced files for this date
    data_path = Path(data_dir)
    pattern = f"{date}_*_AI_enhanced_{language}.jsonl"
    enhanced_files = list(data_path.glob(pattern))
    
    if not enhanced_files:
        logger.warning(f"No AI-enhanced files found for date {date} with pattern: {pattern}")
        return None
    
    logger.info(f"Found {len(enhanced_files)} AI-enhanced files for {date}")
    
    # Load all papers from all files
    all_papers = []
    for file_path in enhanced_files:
        try:
            papers = load_jsonl_data(str(file_path))
            logger.info(f"Loaded {len(papers)} papers from {file_path.name}")
            all_papers.extend(papers)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            continue
    
    if not all_papers:
        logger.warning(f"No papers loaded for date {date}")
        return None
    
    logger.info(f"Total papers to convert: {len(all_papers)}")
    
    # Load template and convert
    try:
        template = load_template()
        markdown = convert_papers_to_markdown(all_papers, date, template)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"Successfully generated MD file: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to convert papers to markdown: {e}")
        return None


def convert_to_md_main(
    date: str,
    data_dir: str = "data",
    language: str = "Chinese"
) -> Optional[str]:
    """Main entry point for MD conversion, to be called from main.py.
    
    This function checks if the MD file for the given date already exists.
    If not, it converts the AI-enhanced JSONL files to markdown format.
    
    Args:
        date: Date string in format 'YYYY-MM-DD'
        data_dir: Base data directory
        language: Language for AI-enhanced files
        
    Returns:
        Path to the generated markdown file, or None if skipped/failed
    """
    logger.info("="*60)
    logger.info(f"Starting MD Conversion for {date}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Language: {language}")
    logger.info("="*60)
    
    result = convert_date_to_md(date, data_dir, language, force=True)
    
    if result:
        logger.info(f"MD conversion completed: {result}")
    else:
        logger.info(f"MD conversion skipped or failed for {date}")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert AI-enhanced JSONL to Markdown")
    parser.add_argument("--date", type=str, required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--data-dir", type=str, default="data", help="Data directory")
    parser.add_argument("--language", type=str, default="Chinese", help="Language suffix")
    parser.add_argument("--force", action="store_true", help="Force regeneration")
    
    args = parser.parse_args()
    
    result = convert_date_to_md(
        date=args.date,
        data_dir=args.data_dir,
        language=args.language,
        force=args.force
    )
    
    if result:
        print(f"Generated: {result}")
    else:
        print("No file generated.")