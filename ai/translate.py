import os
import json
from typing import List, Dict
from pathlib import Path
from tqdm import tqdm

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger
from config import config

logger = get_logger(__name__)


class SummaryTranslator:
    """
    Translator for paper summaries using LLM.
    
    Translates original abstracts to the target language after AI enhancement is complete.
    """
    
    def __init__(self, model_name: str, language: str = "Chinese"):
        """
        Initialize translator.
        
        Args:
            model_name: LLM model name (e.g., 'gpt-oss-20b')
            language: Target language for translation
        """
        self.model_name = model_name
        self.language = language
        self.translation_chain = self._create_translation_chain()
        
        logger.info(f"Initialized SummaryTranslator with model: {model_name}, language: {language}")
        logger.info(f"Using API base URL: {config.NEWAPI_BASE_URL}")
    
    def _create_translation_chain(self):
        """
        Create a LLM chain for translating text.
        
        Returns:
            Configured translation LLM chain
        """
        logger.info(f"Creating translation chain with model: {self.model_name}")
        
        if 'deepseek' in self.model_name:
            llm = ChatDeepSeek(
                model=self.model_name,
                api_base=config.NEWAPI_BASE_URL,
                api_key=config.NEWAPI_KEY_AD,
                max_tokens=4000
            )
        else:
            llm = ChatOpenAI(
                model=self.model_name,
                base_url=config.NEWAPI_BASE_URL,
                api_key=config.NEWAPI_KEY_AD,
                max_tokens=4000
            )
        
        translation_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional translator specialized in academic papers. Translate the given text accurately while preserving technical terminology and academic style."),
            ("user", "Translate the following abstract to {language}. Only output the translated text, no explanations:\n\n{content}")
        ])
        
        return translation_prompt | llm
    
    def _translate_single_paper(self, paper: Dict, source: str) -> bool:
        """
        Translate the summary of a single paper.
        
        Args:
            paper: Paper data dictionary
            source: Source identifier for logging
            
        Returns:
            True if translation was performed, False otherwise
        """
        # Skip if no AI data or AI is Skip
        if not paper.get('AI') or paper['AI'] == 'Skip':
            return False
        
        # Skip if already has translation
        if isinstance(paper['AI'], dict) and 'summary_translated' in paper['AI']:
            return False
        
        summary = paper.get('summary', '')
        if not summary or summary.strip() == '':
            if isinstance(paper['AI'], dict):
                paper['AI']['summary_translated'] = "No Summary Available."
            return False
        
        try:
            response = self.translation_chain.invoke({
                "language": self.language,
                "content": summary
            })
            translated = response.content if hasattr(response, 'content') else str(response)
            if isinstance(paper['AI'], dict):
                paper['AI']['summary_translated'] = translated
            logger.debug(f"[{source}] Successfully translated summary for {paper['id']}")
            return True
        except Exception as e:
            logger.error(f"[{source}] Failed to translate summary for {paper['id']}: {e}")
            if isinstance(paper['AI'], dict):
                paper['AI']['summary_translated'] = "Translation failed."
            return False
    
    def translate_files(self, file_paths: List[str]) -> int:
        """
        Translate summaries in all given files.
        
        Args:
            file_paths: List of enhanced JSONL file paths
            
        Returns:
            Total number of summaries translated
        """
        if not file_paths:
            logger.info("No files to translate")
            return 0
        
        logger.info("="*60)
        logger.info("Starting Summary Translation Phase")
        logger.info(f"Translating summaries in {len(file_paths)} file(s) to {self.language}")
        logger.info("="*60)
        
        # Collect all papers that need translation
        all_papers_by_file = {}  # {file_path: [papers]}
        total_to_translate = 0
        
        for file_path in file_paths:
            try:
                papers = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            papers.append(json.loads(line))
                all_papers_by_file[file_path] = papers
                
                # Count papers needing translation
                for p in papers:
                    if (p.get('AI') and p['AI'] != 'Skip' 
                        and isinstance(p['AI'], dict) 
                        and 'summary_translated' not in p['AI']
                        and p.get('summary') and p['summary'].strip()):
                        total_to_translate += 1
                        
            except Exception as e:
                logger.error(f"Failed to load papers from {file_path}: {e}")
        
        if total_to_translate == 0:
            logger.info("No papers need translation")
            return 0
        
        logger.info(f"Found {total_to_translate} papers needing translation across all files")
        
        # Translate papers in each file
        translated_count = 0
        for file_path, papers in all_papers_by_file.items():
            source = Path(file_path).stem.split('_')[1] if '_' in Path(file_path).stem else 'unknown'
            file_translated = 0
            
            for paper in tqdm(papers, desc=f"Translating {source}"):
                if self._translate_single_paper(paper, source):
                    file_translated += 1
                    translated_count += 1
            
            # Save updated papers back to file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for paper in papers:
                        f.write(json.dumps(paper, ensure_ascii=False) + '\n')
                logger.info(f"[{source}] Translated {file_translated} summaries, saved to {file_path}")
            except Exception as e:
                logger.error(f"[{source}] Failed to save translated papers to {file_path}: {e}")
        
        logger.info(f"Translation complete: {translated_count} summaries translated")
        return translated_count


def process_multi_source_files(data_pattern: str, translator: SummaryTranslator, data_dir: str = "data") -> List[str]:
    """
    Find and process multiple enhanced JSONL files from different sources.
    
    Args:
        data_pattern: Pattern to match files (e.g., '2025-10-31')
        translator: SummaryTranslator instance
        data_dir: Directory containing the files
        
    Returns:
        List of processed file paths
    """
    # Find all matching enhanced files with pattern
    data_path = Path(data_dir)
    files = list(data_path.glob(f"{data_pattern}_*_AI_enhanced_{translator.language}.jsonl"))
    files = [str(f) for f in files]
    
    if not files:
        logger.warning(f"No enhanced files found matching pattern: {data_pattern}")
        return []
    
    logger.info(f"Found {len(files)} enhanced files to translate: {files}")
    
    # Translate all files
    translator.translate_files(files)
    
    return files


def translate_main(data='0000-00-00', data_dir='data', model_name='qwen3-30b-a3b-instruct-2507',
                   language='Chinese'):
    """
    Main function for summary translation.
    
    Args:
        data: File pattern (date) to match files (e.g., '2025-10-31')
        data_dir: Directory containing data files
        model_name: LLM model name
        language: Target language for translation
    """
    # Skip if language is English
    if language.lower() == 'english':
        logger.info("Language is English, skipping translation")
        return
    
    logger.info("="*60)
    logger.info("Starting Summary Translation")
    logger.info(f"Data pattern: {data}")
    logger.info(f"Model: {model_name}")
    logger.info(f"Language: {language}")
    logger.info("="*60)
    
    # Create translator
    translator = SummaryTranslator(
        model_name=model_name,
        language=language
    )
    
    # Process multiple source files
    processed_files = process_multi_source_files(data, translator, data_dir)
    
    logger.info("="*60)
    logger.info("Translation Summary")
    logger.info(f"Successfully translated {len(processed_files)} file(s)")
    for file_path in processed_files:
        logger.info(f"  - {file_path}")
    logger.info("="*60)


if __name__ == "__main__":
    translate_main(data='2025-12-08')
