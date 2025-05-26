import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv

# Danh sách URLs và categories cần crawl
CRAWL_TARGETS = [
    {
        "url": "https://tuyensinh.ctu.edu.vn/",
        "category": "tuyen_sinh_general",
        "description": "Thông tin tuyển sinh tổng quát",
        "prompt": "Extract general admission information, overview, and basic Q&A pairs in Vietnamese"
    },
    {
        "url": "https://tuyensinh.ctu.edu.vn/danh-muc-nganh-va-chi-tieu-tuyen-sinh",
        "category": "nganh_hoc", 
        "description": "Danh sách ngành và chỉ tiêu",
        "prompt": "Extract major names, codes, quotas, and related Q&A pairs in Vietnamese"
    },
    {
        "url": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen",
        "category": "phuong_thuc_xet_tuyen",
        "description": "Phương thức xét tuyển",
        "prompt": "Extract admission methods, requirements, deadlines, and related Q&A pairs in Vietnamese"
    },
    {
        "url": "https://tuyensinh.ctu.edu.vn/hoc-phi",
        "category": "hoc_phi",
        "description": "Thông tin học phí",
        "prompt": "Extract tuition fees, payment methods, scholarships, and related Q&A pairs in Vietnamese"
    },
    {
        "url": "https://tuyensinh.ctu.edu.vn/lien-he",
        "category": "lien_he",
        "description": "Thông tin liên hệ",
        "prompt": "Extract contact information, office hours, locations, and related Q&A pairs in Vietnamese"
    }
]

async def crawl_single_category(crawler, target, api_key, output_dir):
    """
    Crawl một category riêng biệt
    """
    print(f"\n🔍 Đang crawl: {target['description']}")
    print(f"📍 URL: {target['url']}")
    
    # Tạo prompt cụ thể cho category
    instruction = f"""
    You are extracting data for category: {target['category']}
    
    {target['prompt']}
    
    Focus on:
    - Creating natural Vietnamese Q&A pairs
    - Extracting specific information for this category
    - Maintaining accuracy and completeness
    - Using proper Vietnamese language
    
    Return structured data with Q&A pairs and relevant information.
    """
    
    # Schema đơn giản cho từng category
    schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string"},
            "qa_pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "priority": {"type": "integer"}
                    }
                }
            },
            "structured_data": {"type": "object"},
            "metadata": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "category": {"type": "string"},
                    "crawl_date": {"type": "string"}
                }
            }
        }
    }
    
    # Configure LLM strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key
        ),
        schema=schema,
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1000,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 3000}
    )
    
    # Configure crawler run
    run_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )
    
    try:
        # Run crawler
        result = await crawler.arun(url=target['url'], config=run_config)
        
        if result.success and result.extracted_content:
            # Parse extracted data
            extracted_data = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
            
            # Add metadata
            if isinstance(extracted_data, dict):
                extracted_data['metadata'] = {
                    'url': target['url'],
                    'category': target['category'],
                    'description': target['description'],
                    'crawl_date': datetime.now().isoformat(),
                    'success': True
                }
            
            # Save to category-specific file
            output_file = Path(output_dir) / f"{target['category']}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            # Save raw markdown
            markdown_file = Path(output_dir) / f"{target['category']}.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(result.markdown.raw_markdown if hasattr(result, 'markdown') and result.markdown else "")
            
            print(f"✅ Thành công: {output_file}")
            return extracted_data
            
        else:
            print(f"❌ Lỗi crawl: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

async def main():
    """
    Main function để crawl tất cả categories
    """
    # Load environment
    load_dotenv(override=True)
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Không tìm thấy OPENAI_API_KEY!")
        return
    
    # Setup output directory
    output_dir = "output/categories"
    os.makedirs(output_dir, exist_ok=True)
    
    # Browser config
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    print("🚀 Bắt đầu crawl theo categories...")
    print(f"📁 Output directory: {output_dir}")
    
    results = {}
    
    # Crawl each category
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for target in CRAWL_TARGETS:
            result = await crawl_single_category(crawler, target, api_key, output_dir)
            results[target['category']] = result
            
            # Delay between requests
            await asyncio.sleep(2)
    
    # Create summary
    summary = {
        "crawl_summary": {
            "total_categories": len(CRAWL_TARGETS),
            "successful_crawls": len([r for r in results.values() if r is not None]),
            "failed_crawls": len([r for r in results.values() if r is None]),
            "crawl_date": datetime.now().isoformat(),
            "categories": list(results.keys())
        },
        "results": results
    }
    
    # Save summary
    summary_file = Path(output_dir) / "crawl_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Tổng kết:")
    print(f"   ✅ Thành công: {summary['crawl_summary']['successful_crawls']}")
    print(f"   ❌ Thất bại: {summary['crawl_summary']['failed_crawls']}")
    print(f"   📄 Summary: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main()) 