import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.async_configs import LLMConfig
from models.admission_schema import AdmissionDataSchema


async def process_markdown_to_json(markdown_file_path: str, output_dir: str = "output"):
    """
    Process existing markdown file and extract structured JSON data using LLM.
    
    Args:
        markdown_file_path: Path to the markdown file to process
        output_dir: Directory to save results
    """
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
        return
    
    # Read the markdown file
    try:
        with open(markdown_file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
    except FileNotFoundError:
        print(f"Error: File {markdown_file_path} not found.")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Load instruction from file
    try:
        with open("prompts/extraction_prompt.txt", "r", encoding="utf-8") as f:
            instruction = f.read()
    except FileNotFoundError:
        print("Warning: extraction_prompt.txt not found. Using default instruction.")
        instruction = """
        Trích xuất thông tin từ nội dung website Đại học Cần Thơ để tạo dữ liệu huấn luyện chatbot tư vấn tuyển sinh.
        
        Hãy tạo các cặp câu hỏi-trả lời (Q&A pairs) từ thông tin có sẵn, bao gồm:
        - Thông tin về các ngành học
        - Phương thức xét tuyển  
        - Học phí và chính sách học bổng
        - Thông tin liên hệ
        - Thông tin chung về trường
        
        Mỗi câu hỏi nên tự nhiên như người dùng thật sẽ hỏi, và câu trả lời phải chính xác, hữu ích.
        """
    
    # Configure LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key
        ),
        schema=AdmissionDataSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=2000,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 8000}
    )
    
    print(f"Processing markdown file: {markdown_file_path}")
    print(f"Content length: {len(markdown_content)} characters")
    
    try:
        # Extract structured data from markdown content
        extracted_content = await llm_strategy.aextract(
            url="file://local",  # Dummy URL since we're processing local content
            html="",  # Empty HTML since we're using markdown
            markdown=markdown_content
        )
        
        if extracted_content:
            print("\nExtraction successful!")
            
            # Parse the extracted JSON
            try:
                if isinstance(extracted_content, str):
                    extracted_data = json.loads(extracted_content)
                else:
                    extracted_data = extracted_content
                
                print("Extracted data preview:")
                print(json.dumps(extracted_data, indent=2, ensure_ascii=False)[:1000] + "...")
                
                # Save the extracted JSON
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True, parents=True)
                
                # Create output filename
                input_filename = Path(markdown_file_path).stem
                json_file = output_path / f"{input_filename}_extracted.json"
                
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                
                print(f"\nExtracted JSON saved to: {json_file}")
                
                # Show statistics
                if isinstance(extracted_data, dict):
                    if 'qa_pairs' in extracted_data:
                        print(f"Number of Q&A pairs extracted: {len(extracted_data['qa_pairs'])}")
                    if 'intents' in extracted_data:
                        print(f"Intents found: {list(extracted_data['intents'].keys())}")
                
                return extracted_data
                
            except json.JSONDecodeError as e:
                print(f"Error parsing extracted JSON: {e}")
                print("Raw extracted content:")
                print(extracted_content)
                return None
                
        else:
            print("No content was extracted.")
            return None
            
    except Exception as e:
        print(f"Error during extraction: {e}")
        return None


async def main():
    """Main function to process the crawl result markdown file."""
    load_dotenv(override=True)
    
    markdown_file = "output/crawl_result.md"
    output_dir = "output"
    
    # Check if the markdown file exists
    if not os.path.exists(markdown_file):
        print(f"Error: {markdown_file} not found.")
        print("Please make sure you have the crawl_result.md file in the output directory.")
        return
    
    print("Starting markdown to JSON conversion...")
    result = await process_markdown_to_json(markdown_file, output_dir)
    
    if result:
        print("\n✅ Conversion completed successfully!")
    else:
        print("\n❌ Conversion failed.")


if __name__ == "__main__":
    asyncio.run(main()) 