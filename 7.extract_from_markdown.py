import asyncio
import json
import os
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, LLMConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv
from models.admission_schema import AdmissionDataSchema
from openai import AsyncOpenAI


async def extract_from_markdown(md_file_path, output_dir="output"):
    """
    Extract structured JSON data from markdown file using LLM.
    
    Args:
        md_file_path: Path to markdown file
        output_dir: Directory to save results
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
    
    # Load instruction from file or use default
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
    
    # Configure LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key
        ),
        schema=AdmissionDataSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1500,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 5000}
    )
    
    # Configure browser (dummy, just for LLM extraction)
    browser_config = BrowserConfig(headless=True, verbose=False)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Alternative approach: Create a mock URL and use the extraction strategy
            # through the crawler's normal process but with our markdown content
            
            # Create a temporary HTML file with our markdown content
            temp_html = f"""
            <html>
            <head><title>CTU Admission Data</title></head>
            <body>
            <pre>{markdown_content}</pre>
            </body>
            </html>
            """
            
            # Use the extraction strategy directly with proper parameters
            try:
                # Method 1: Try with named parameters
                extracted_data = await llm_strategy.extract(content=markdown_content, html=temp_html)
            except Exception as e1:
                print(f"⚠️ Method 1 failed: {e1}")
                try:
                    # Method 2: Try with positional parameters
                    extracted_data = await llm_strategy.extract(markdown_content, temp_html)
                except Exception as e2:
                    print(f"⚠️ Method 2 failed: {e2}")
                    # Method 3: Use crawler with data URL
                    data_url = "data:text/html;charset=utf-8," + temp_html.replace(" ", "%20").replace("\n", "%0A")
                    
                    # Direct LLM call approach
                    client = AsyncOpenAI(api_key=api_key)
                    
                    prompt = f"""
                    {instruction}
                    
                    Content to analyze:
                    {markdown_content}
                    
                    Please extract the data according to the schema and return valid JSON.
                    """
                    
                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        max_tokens=5000
                    )
                    
                    extracted_data = response.choices[0].message.content
            
            if extracted_data:
                # Parse extracted data
                if isinstance(extracted_data, str):
                    extracted_data = json.loads(extracted_data)
                
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
                print("❌ No data extracted")
                return None
                
    except Exception as e:
        print(f"❌ Exception during extraction: {str(e)}")
        return None


async def main():
    """
    Main function - extract from specific markdown file
    """
    load_dotenv(override=True)
    
    # Configuration
    md_file = "output/crawled_pages/https_tuyensinh.ctu.edu.vn_chuong-trinh-dai-tra_841-danh-muc-nganh-va-chi-tieu-tuyen-sinh-dhcq.html.md"
    output_dir = "output"
    
    print("🚀 Starting extraction from markdown file...")
    print(f"📁 Input: {md_file}")
    print(f"📁 Output: {output_dir}")
    
    # Check if file exists
    if not Path(md_file).exists():
        print(f"❌ File not found: {md_file}")
        print("Available files in output/crawled_pages/:")
        crawled_dir = Path("output/crawled_pages")
        if crawled_dir.exists():
            for file in crawled_dir.glob("*.md"):
                print(f"   📄 {file.name}")
        return
    
    # Extract data
    result_file = await extract_from_markdown(md_file, output_dir)
    
    if result_file:
        print(f"\n🎉 Extraction completed!")
        print(f"📄 Result: {result_file}")
        print(f"\n💡 Next step: Use 3.multi_url_crawler.py to crawl URLs from this JSON")
        print(f"   Command: python 3.multi_url_crawler.py")


if __name__ == "__main__":
    asyncio.run(main()) 