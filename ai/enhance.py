import os
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from pathlib import Path
import dotenv
import argparse
from tqdm import tqdm

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
import langchain_core.exceptions
from langchain.agents.structured_output import ToolStrategy
from ai.structure import Structure

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger_config import get_logger

logger = get_logger(__name__)


class AIEnhancer:
    """
    AI-powered paper enhancement using LLM for structured summarization.
    
    Generates structured summaries (TLDR, motivation, method, results, conclusion)
    for academic papers using OpenAI-compatible LLM APIs.
    """
    
    def __init__(self, model_name: str, language: str = "Chinese", 
                 max_workers: int = 1):
        """
        Initialize AI enhancer.
        
        Args:
            model_name: LLM model name (e.g., 'gpt-oss-20b')
            language: Output language for summaries
            max_workers: Maximum number of parallel workers
        """
        self.model_name = model_name
        self.language = language
        self.max_workers = max_workers
        
        # Load prompt templates
        template_path = Path(__file__).parent / "template.txt"
        system_path = Path(__file__).parent / "system.txt"
        self.template = template_path.read_text(encoding='utf-8')
        self.system = system_path.read_text(encoding='utf-8')
        self.chain = self._create_llm_chain()
        
        logger.info(f"Initialized AIEnhancer with model: {model_name}, language: {language}")
        logger.info(f"Using API base URL: {os.environ.get('NEWAPI_BASE_URL')}")
    
    def _create_llm_chain(self):
        """
        Create LLM chain with prompt templates.
        
        Returns:
            Configured LLM chain
        """
        logger.info(f"Initializing LLM: {self.model_name}")
        if 'deepseek' in self.model_name:
            llm = ChatDeepSeek(
                model=self.model_name,
                api_base=os.environ.get('NEWAPI_BASE_URL'),
                # base_url=self.base_url,
                api_key=os.environ.get('NEWAPI_KEY_AD'),
                max_tokens=7000
            ).with_structured_output(Structure)
            logger.info(f"Connected to DeepSeek LLM: {self.model_name}")
        else:
            llm = ChatOpenAI(
                model=self.model_name,
                base_url=os.environ.get('NEWAPI_BASE_URL'),
                api_key=os.environ.get('NEWAPI_KEY_AD'),
                max_tokens=7000
            ).with_structured_output(Structure)
            logger.info(f"Connected to OpenAI-compatible LLM: {self.model_name}")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system),
            ("user", self.template),
        ])
        
        return prompt_template | llm
    
    def _process_single_item(self, item: Dict, source: str, item_p) -> Dict:
        """
        Process a single paper item.
        
        Args:
            item: Paper data dictionary
            source: str,
            output_file: str
            
        Returns:
            Enhanced paper data with AI summary
        """
        if item and item["score"]["max"] < 3.6:
                logger.debug(f"[{source}] Skipping irrelevant item: {item['id']}")
                item['AI'] = 'Skip'
                return item
        if item_p:
            if 'AI' in item_p and item_p.get('AI', {}).get('tldr') != 'Error':
                logger.debug(f"[{source}] Skipping already processed item: {item['id']}")
                if item['id'] != item_p['id']:
                    logger.error(f"[{source}] Item ID mismatch: {item['id']} != {item_p['id']}")
                    raise ValueError(f"[{source}] Item ID mismatch: {item['id']} != {item_p['id']}")
                item['AI'] = item_p['AI']

                return item
        
        logger.debug(f"[{source}] Processing item: {item['id']}")
        try:
            response = self.chain.invoke({
                "language": self.language,
                "content": item['summary']
            })
            item['AI'] = response.model_dump()
            logger.debug(f"[{source}] Successfully processed item: {item['id']}")
        except langchain_core.exceptions.OutputParserException as e:
            logger.warning(f"[{source}] Output parser exception for {item['id']}: {str(e)[:100]}...")
            error_msg = str(e)
            if "Function Structure arguments:" in error_msg:
                try:
                    json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
                    json_str = json_str.replace('\\', '\\\\')
                    fixed_data = json.loads(json_str)
                    item['AI'] = fixed_data
                    logger.info(f"[{source}] Successfully fixed JSON for {item['id']}")
                    return item
                except Exception as json_e:
                    logger.error(f"[{source}] Failed to fix JSON for {item['id']}: {json_e}")
            item['AI'] = {
                "tldr": "Error",
                "motivation": "Error",
                "method": "Error",
                "result": "Error",
                "conclusion": "Error"
            }
            logger.error(f"[{source}] Set error AI data for {item['id']}")
        except Exception as e:
            logger.error(f"[{source}] Unexpected error processing {item['id']}: {e}")
            item['AI'] = {
                "tldr": "Error",
                "motivation": "Error",
                "method": "Error",
                "result": "Error",
                "conclusion": "Error"
            }
        return item
    
    def enhance_papers(self, papers: List[Dict], source: str, papers_p) -> List[Dict]:
        """
        Enhance multiple papers with AI summaries.
        
        Args:
            papers: List of paper dictionaries
            output_file: str
            source: str
            
        Returns:
            List of enhanced paper dictionaries
        """
        logger.info(f"[{source}] Processing {len(papers)} papers with {self.max_workers} workers")
        
        processed_data = [None] * len(papers)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._process_single_item, item, source, item_p): idx
                for idx, item, item_p in zip(range(len(papers)), papers, papers_p)
            }
            
            for future in tqdm(as_completed(future_to_idx), total=len(papers), desc="Enhancing papers"):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    processed_data[idx] = result
                except Exception as e:
                    logger.error(f"[{source}] Item at index {idx} generated an exception: {e}")
                    processed_data[idx] = papers[idx]
        
        logger.info(f"[{source}] Completed processing {len(papers)} papers")
        return processed_data
    
    def process_file(self, input_file: str, source: str) -> str:
        """
        Process a single JSONL file.
        
        Args:
            input_file: Input JSONL file path
            source: str
            
            output_file: Output file path (auto-generated if None)
            
        Returns:
            Output file path
        """
        logger.info(f"[{source}] Processing file: {input_file}")
        
        # Load papers
        papers = []
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        papers.append(json.loads(line))
            logger.info(f"[{source}] Loaded {len(papers)} papers from {input_file}")
        except Exception as e:
            logger.error(f"[{source}] Failed to load data from {input_file}: {e}")
            raise
        
        # Generate output filename
        input_path = Path(input_file)
        output_file = str(input_path.with_name(f"{input_path.stem}_AI_enhanced_{self.language}.jsonl"))
        if os.path.exists(output_file):
            logger.info(f"[{source}] Output file already exists: {output_file}")
            papers_p = []
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            papers_p.append(json.loads(line))
                logger.info(f"[{source}] Loaded {len(papers_p)} papers from {output_file}")
            except Exception as e:
                logger.error(f"[{source}] Failed to load data from {output_file}: {e}")
                raise
            if len(papers) != len(papers_p):
                logger.warning(f"[{source}] Length of papers ({len(papers)}) and processed papers ({len(papers_p)}) do not match")
            while len(papers) > len(papers_p):
                papers_p.append(None)
            while len(papers_p) > len(papers):
                papers_p.pop()

        else:
            papers_p = [None] * len(papers)

        # Enhance papers
        enhanced_papers = self.enhance_papers(papers, source, papers_p)
        
        # Save enhanced papers
        logger.info(f"[{source}] Saving enhanced papers to {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for paper in enhanced_papers:
                    f.write(json.dumps(paper, ensure_ascii=False) + '\n')
            logger.info(f"[{source}] Successfully saved {len(enhanced_papers)} papers to {output_file}")
        except Exception as e:
            logger.error(f"[{source}] Failed to save data to {output_file}: {e}")
            raise
        
        return output_file

def process_multi_source_files(data_pattern: str, enhancer: AIEnhancer, data_dir: str = "data") -> List[str]:
    """
    Process multiple JSONL files from different sources.
    
    Args:
        data_pattern: Pattern to match files (e.g., '2025-10-31')
        enhancer: AIEnhancer instance
        data_dir: Directory containing the files
        
    Returns:
        List of processed output file paths
    """

    # Find all matching files with pattern
    data_path = Path(data_dir)
    files = list(data_path.glob(f"{data_pattern}_*.jsonl"))
    # Exclude already enhanced files
    files = [str(f) for f in files if '_AI_enhanced_' not in f.name]
    
    if not files:
        logger.warning(f"No files found matching pattern: {data_pattern}")
        return []
    
    logger.info(f"Found {len(files)} files to enhance: {files}")
    processed_files = []
    
    for file_path in files:
        source = Path(file_path).stem.split('_')[-1] if '_' in Path(file_path).stem else 'unknown'
        try:
            logger.info(f"="*60)
            logger.info(f"Processing file: {file_path}")
            
            # Detect source from filename
            logger.info(f"Detected source: {source}")
            logger.info(f"="*60)
            
            # Process file
            output_file = enhancer.process_file(file_path, source)
            
            logger.info(f"[{source}] Successfully enhanced {file_path} -> {output_file}")
            processed_files.append(output_file)
            
        except Exception as e:
            logger.error(f"[{source}] Failed to process {file_path}: {e}", exc_info=True)
    
    return processed_files


def enhance_main(data='0000-00-00', data_dir='data', model_name='gpt-oss-20b', 
                 language='Chinese', max_workers=1):
    """
    Main function for AI enhancement.
    
    Args:
        data: File pattern or comma-separated file paths
        data_dir: Directory containing data files
        model_name: LLM model name
        language: Output language
        max_workers: Maximum parallel workers
    """
    logger.info("="*60)
    logger.info("Starting AI Enhancement (Multi-Source)")
    logger.info(f"Data pattern: {data}")
    logger.info(f"Model: {model_name}")
    logger.info(f"Language: {language}")
    logger.info(f"Max workers: {max_workers}")
    logger.info("="*60)
    
    # Create enhancer
    enhancer = AIEnhancer(
        model_name=model_name,
        language=language,
        max_workers=max_workers
    )
    
    # Process multiple source files
    processed_files = process_multi_source_files(data, enhancer, data_dir)
    
    logger.info("="*60)
    logger.info("Enhancement Summary")
    logger.info(f"Successfully enhanced {len(processed_files)} file(s)")
    for file_path in processed_files:
        logger.info(f"  - {file_path}")
    logger.info("="*60)

if __name__ == "__main__":
    enhance_main()
