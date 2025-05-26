import asyncio
import json
import os
import tempfile
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv
from models.admission_schema import AdmissionDataSchema


async def extract_from_markdown_simple(md_file_path, output_dir="output"):
    """
    Extract structured JSON data from markdown file using proven crawler approach.
    """
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return None
    
    # Read markdown content
    try:
        with open(md_file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        print(f"📄 Loaded markdown: {len(markdown_content)} characters")
    except FileNotFoundError:
        print(f"❌ File not found: {md_file_path}")
        return None
    
    # Load instruction
    try:
        with open("prompts/extraction_prompt.txt", "r", encoding="utf-8") as f:
            instruction = f.read()
    except FileNotFoundError:
        print("⚠️ extraction_prompt.txt not found. Using default instruction.")
        instruction = """
        Bạn là chuyên gia tư vấn tuyển sinh Đại học Cần Thơ (CTU). 
        Hãy phân tích nội dung và tạo ra các cặp hỏi-đáp tiếng Việt tự nhiên mà sinh viên thường hỏi.
        
        QUAN TRỌNG:
        - Tất cả câu hỏi và câu trả lời phải bằng tiếng Việt
        - Tạo câu hỏi tự nhiên như sinh viên thật sự hỏi
        - Trả lời chi tiết, chính xác dựa trên nội dung
        - Extract URLs để crawl tiếp
        - Bao gồm mã ngành, chỉ tiêu, học phí, tổ hợp xét tuyển
        """
    
    # Create temporary HTML file in current directory instead of temp
    temp_filename = f"temp_extraction_{os.getpid()}.html"
    temp_file_path = os.path.abspath(temp_filename)
    
    try:
        # Create temporary HTML content
        temp_html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>CTU Admission Data</title>
        </head>
        <body>
            <div id="content">
                <pre>{markdown_content}</pre>
            </div>
        </body>
        </html>
        """
        
        # Write HTML content to file
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(temp_html_content)
        
        # Convert to proper file:// URL for Windows
        if os.name == 'nt':  # Windows
            file_url = f"file:///{temp_file_path.replace(os.sep, '/')}"
        else:  # Unix/Linux
            file_url = f"file://{temp_file_path}"
            
        print(f"🔗 Using temporary file: {temp_file_path}")
        print(f"🔗 Using URL: {file_url}")
        
        # Verify file exists
        if not os.path.exists(temp_file_path):
            print(f"❌ Temporary file not created: {temp_file_path}")
            return None
        
        # Configure browser settings (same as 2.llm_extract.py)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Configure LLM extraction strategy (same as 2.llm_extract.py)
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider="openai/gpt-4o-mini",
                api_token=api_key
            ),
            schema=AdmissionDataSchema.model_json_schema(),
            extraction_type="schema",
            instruction=instruction,
            chunk_token_threshold=1000,
            overlap_rate=0.0,
            apply_chunking=True,
            input_format="markdown",
            extra_args={"temperature": 0.0, "max_tokens": 5000}
        )
        
        # Configure the crawler run (same as 2.llm_extract.py)
        run_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS
        )
        
        # Run crawler (same as 2.llm_extract.py)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=file_url, config=run_config)
            
            if result.success and hasattr(result, 'extracted_content') and result.extracted_content:
                print("✅ Extraction successful!")
                
                # Process extracted content (same as 2.llm_extract.py)
                extracted_data = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
                
                # Create output directory
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True, parents=True)
                
                # Generate filename from input file
                input_name = Path(md_file_path).stem
                json_file = output_path / f"{input_name}_extracted.json"
                
                # Save extracted JSON
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Extracted data saved to: {json_file}")
                
                # Show summary
                if isinstance(extracted_data, list) and len(extracted_data) > 0:
                    first_chunk = extracted_data[0]
                    qa_count = len(first_chunk.get('qa_pairs', []))
                    url_count = len(first_chunk.get('extracted_urls', []))
                    print(f"📊 Summary:")
                    print(f"   📝 Q&A pairs: {qa_count}")
                    print(f"   🔗 URLs found: {url_count}")
                    
                    # Show extracted URLs
                    if url_count > 0:
                        print(f"🔗 URLs to crawl next:")
                        for url_info in first_chunk.get('extracted_urls', [])[:5]:
                            print(f"   - {url_info.get('text', 'N/A')}: {url_info.get('url', 'N/A')}")
                        if url_count > 5:
                            print(f"   ... and {url_count - 5} more URLs")
                
                return json_file
                
            else:
                print(f"❌ Extraction failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
                return None
                
    except Exception as e:
        print(f"❌ Exception during extraction: {str(e)}")
        return None
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass


async def main():
    """
    Main function - extract from specific markdown file
    """
    load_dotenv(override=True)
    
    # Configuration
    md_file = "output/crawled_pages_level2/https_tuyensinh.ctu.edu.vn_chuong-trinh-dai-tra_841-danh-muc-nganh-va-chi-tieu-tuyen-sinh-dhcq.html.md"
    output_dir = "output"
    
    print("🚀 Starting simple extraction from markdown file...")
    print(f"📁 Input: {md_file}")
    print(f"📁 Output: {output_dir}")
    
    # Check if file exists
    if not Path(md_file).exists():
        print(f"❌ File not found: {md_file}")
        print("Available files in output/crawled_pages_level2/:")
        crawled_dir = Path("output/crawled_pages_level2")
        if crawled_dir.exists():
            for file in crawled_dir.glob("*.md"):
                print(f"   📄 {file.name}")
        else:
            print("   Directory not found. Try running 3.multi_url_crawler.py first.")
        return
    
    # Extract data
    result_file = await extract_from_markdown_simple(md_file, output_dir)
    
    if result_file:
        print(f"\n🎉 Extraction completed!")
        print(f"📄 Result: {result_file}")
        print(f"\n💡 Next step: Use 3.multi_url_crawler.py to crawl URLs from this JSON")
        print(f"   Command: python 3.multi_url_crawler.py")


if __name__ == "__main__":
    asyncio.run(main()) 