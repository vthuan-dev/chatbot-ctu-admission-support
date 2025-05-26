import asyncio
import json
import os
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv
from models.admission_schema import AdmissionDataSchema


async def main():
    """
    Crawl the specific CTU admission page and extract structured JSON data using LLM.
    This is the proven approach from 2.llm_extract.py but targeting the specific page.
    """
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return
    
    # Configure browser settings
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Load instruction from file
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
        - Tạo nhiều Q&A pairs từ thông tin chi tiết về ngành học
        """
    
    # Target the specific detailed admission page
    url = "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/841-danh-muc-nganh-va-chi-tieu-tuyen-sinh-dhcq.html"
    
    print(f"🎯 Target URL: {url}")
    print("📊 This page contains detailed major information with codes, quotas, and admission combinations")
    
    # Configure LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key
        ),
        schema=AdmissionDataSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1500,  # Increased for detailed content
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 6000}  # Increased for more Q&A pairs
    )
    
    # Configure the crawler run
    run_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )
        
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("🚀 Starting extraction from detailed admission page...")
        
        # Run the crawler with LLM extraction
        result = await crawler.arun(url=url, config=run_config)
        
        # Display results
        print(f"Crawl successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
            return
        
        # Process extracted content
        if hasattr(result, 'extracted_content') and result.extracted_content:
            print("\n✅ Extraction successful!")
            try:
                extracted_data = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
                
                # Save the extracted JSON
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True, parents=True)
                
                # Create filename from URL
                url_filename = "ctu_detailed_majors_extracted"
                
                # Save JSON and markdown
                json_file = output_path / f"{url_filename}.json"
                markdown_file = output_path / f"{url_filename}.md"
                
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                
                with open(markdown_file, "w", encoding="utf-8") as f:
                    f.write(result.markdown.raw_markdown if hasattr(result, 'markdown') and result.markdown else "")
                
                print(f"📄 Extracted JSON saved to: {json_file}")
                print(f"📄 Markdown content saved to: {markdown_file}")
                
                # Show summary
                if isinstance(extracted_data, list) and len(extracted_data) > 0:
                    first_chunk = extracted_data[0]
                    qa_count = len(first_chunk.get('qa_pairs', []))
                    url_count = len(first_chunk.get('extracted_urls', []))
                    print(f"\n📊 Extraction Summary:")
                    print(f"   📝 Q&A pairs: {qa_count}")
                    print(f"   🔗 URLs found: {url_count}")
                    
                    # Show sample Q&A
                    if qa_count > 0:
                        print(f"\n📝 Sample Q&A (first 3):")
                        for i, qa in enumerate(first_chunk.get('qa_pairs', [])[:3], 1):
                            print(f"   {i}. Q: {qa.get('question', 'N/A')}")
                            print(f"      A: {qa.get('answer', 'N/A')[:100]}...")
                            print(f"      Category: {qa.get('category', 'N/A')}")
                            print()
                    
                    # Show extracted URLs
                    if url_count > 0:
                        print(f"🔗 URLs for next crawl:")
                        for url_info in first_chunk.get('extracted_urls', [])[:3]:
                            print(f"   - {url_info.get('text', 'N/A')}: {url_info.get('url', 'N/A')}")
                        if url_count > 3:
                            print(f"   ... and {url_count - 3} more URLs")
                
                print(f"\n🎉 Success! You now have detailed Q&A data about CTU majors!")
                print(f"💡 Next: Use 3.multi_url_crawler.py to crawl more URLs from this extraction")
                
            except Exception as e:
                print(f"Error processing extracted content: {e}")
        else:
            print("\n❌ No structured data was extracted or extraction failed.")

if __name__ == "__main__":
    load_dotenv(override=True)
    asyncio.run(main()) 