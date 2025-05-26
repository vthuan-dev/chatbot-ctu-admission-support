import asyncio
import os
import json
import sys
from pathlib import Path
from typing import List
from crawl4ai import (
    AsyncWebCrawler, 
    CrawlerRunConfig, 
    CacheMode, 
    BrowserConfig, 
    SemaphoreDispatcher, 
    RateLimiter
)

def load_extracted_urls(json_file):
    """
    Load URLs from previous extraction result
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    urls_to_crawl = []
    
    for chunk in data:
        if 'extracted_urls' in chunk and chunk['extracted_urls']:
            for url_info in chunk['extracted_urls']:
                # Skip PDFs and other non-web content, but include all web URLs
                if not url_info['url'].endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                    urls_to_crawl.append({
                        'url': url_info['url'],
                        'category': url_info['category'],
                        'priority': url_info['priority'],
                        'description': url_info['text']
                    })
    
    return urls_to_crawl

async def read_urls_from_json(file_path: str, max_priority: int = 2, target_categories: List[str] = None) -> List[str]:
    """Read URLs from a JSON file containing a list of ResultSchema objects."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    urls = []
    
    # Check if this is the new QA format with qa_pairs
    if isinstance(data, dict) and 'qa_pairs' in data:
        # Extract URLs from qa_pairs source_url fields
        for qa_pair in data['qa_pairs']:
            if isinstance(qa_pair, dict) and 'source_url' in qa_pair:
                url = qa_pair['source_url']
                # Skip PDFs and other non-web content
                if not url.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                    if url not in urls:  # Avoid duplicates
                        urls.append(url)
        return urls
    
    # Check if this is the new CTU URLs format (from tuyen_sinh_ctu_urls.json)
    elif isinstance(data, dict) and 'urls' in data and 'total_urls' in data:
        # CTU URLs format with priority and category
        print(f"📊 CTU URLs data: {data['total_urls']} total, {data['high_priority_urls']} high priority")
        print(f"🔍 Filters: max_priority={max_priority}, categories={target_categories or 'all'}")
        
        category_stats = {}
        
        for url_info in data['urls']:
            if isinstance(url_info, dict) and 'url' in url_info:
                # Skip PDFs and other non-web content
                if not url_info['url'].endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                    priority = url_info.get('priority', 3)
                    category = url_info.get('category', 'unknown')
                    
                    # Count by category
                    if category not in category_stats:
                        category_stats[category] = {'total': 0, 'selected': 0}
                    category_stats[category]['total'] += 1
                    
                    # Filter by priority and category
                    if priority <= max_priority:
                        if not target_categories or category in target_categories:
                            urls.append(url_info['url'])
                            category_stats[category]['selected'] += 1
                            print(f"  ➡️ Priority {priority} [{category}]: {url_info.get('text', url_info['url'])[:80]}...")
        
        # Display category statistics
        print(f"\n📂 Category Statistics:")
        for category, stats in sorted(category_stats.items()):
            print(f"  {category}: {stats['selected']}/{stats['total']} selected")
        
        print(f"✅ Selected {len(urls)} URLs for crawling (priority ≤ {max_priority})")
        return urls
    
    # Check if this is the old extraction result format (from 2.llm_extract.py)
    elif isinstance(data, dict) and 'urls' in data:
        # Old format from LLM extraction
        for url_info in data['urls']:
            if isinstance(url_info, dict) and 'url' in url_info:
                # Skip PDFs and other non-web content
                if not url_info['url'].endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                    urls.append(url_info['url'])
        return urls
    
    # Check if this is old extraction result format
    elif isinstance(data, list) and len(data) > 0 and 'extracted_urls' in data[0]:
        # Old format - extract URLs from extracted_urls field
        url_infos = load_extracted_urls(file_path)
        return [info['url'] for info in url_infos]
    
    # Original format - extract URLs from ResultSchema objects
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'url' in item:
                urls.append(item['url'])
        return urls
    
    else:
        print(f"⚠️ Unknown JSON format in {file_path}")
        return []

async def crawl_urls(
    urls: List[str], 
    semaphore_count: int = 5,
    check_robots_txt: bool = True,
    cache_mode: CacheMode = CacheMode.ENABLED,
    output_dir: str = None
):
    """Crawl multiple URLs with semaphore-based concurrency and robots.txt respect."""
    browser_config = BrowserConfig(
        headless=True, 
        verbose=False
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=cache_mode,
        check_robots_txt=check_robots_txt,  # Respect robots.txt
        stream=False  # Disable streaming results to fix compatibility with SemaphoreDispatcher
    )

    # Configure dispatcher with semaphore and rate limiting
    dispatcher = SemaphoreDispatcher(
        semaphore_count=semaphore_count,  # Control concurrency
        rate_limiter=RateLimiter(
            base_delay=(1.0, 2.0),  # Random delay between 1 and 2 seconds
            max_delay=10.0  # Maximum delay after backoff
        )
    )

    # Setup output directory if provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

    print(f"Starting crawl of {len(urls)} URLs with semaphore count: {semaphore_count}")
    print(f"Robots.txt checking: {'Enabled' if check_robots_txt else 'Disabled'}")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls, 
            config=run_config,
            dispatcher=dispatcher
        )
        
        for result in results:
            if result.success:
                content_length = len(result.markdown.raw_markdown) if result.markdown else 0
                print(f"✅ {result.url} - {content_length} characters")
                
                # Save content to file if output directory is specified
                if output_dir:
                    url_filename = result.url.replace("://", "_").replace("/", "_").replace("?", "_")
                    if len(url_filename) > 100:
                        url_filename = url_filename[:100]  # Prevent extremely long filenames
                    
                    output_file = output_path / f"{url_filename}.md"
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(result.markdown.raw_markdown if result.markdown else "")
                    print(f"   Saved to {output_file}")
            else:
                error_message = result.error_message or "Unknown error"
                if result.status_code == 403 and "robots.txt" in error_message:
                    print(f"🚫 {result.url} - Blocked by robots.txt")
                else:
                    print(f"❌ {result.url} - Error: {error_message}")
        
        return results

async def main():
    # 🎯 Configuration - Get JSON file from command line or use default
    if len(sys.argv) > 1:
        input_json_file = sys.argv[1]
        print(f"📝 Using JSON file from command line: {input_json_file}")
    else:
        # 👇 Default JSON file - CTU Admission URLs
        input_json_file = "output/processed/tuyen_sinh_ctu/tuyen_sinh_ctu_urls.json"  
        print(f"📝 Using default CTU admission URLs file: {input_json_file}")
        print(f"💡 You can also specify a file: python {sys.argv[0]} your_file.json")
    
    # 📋 Other available options (uncomment to use):
    # input_json_file = "output/processed/tuyen_sinh_ctu/tuyen_sinh_ctu_qa.json"
    # input_json_file = "data/processed/nganh_hoc/nganh_hoc_qa.json"
    # input_json_file = "data/processed/xet_tuyen/xet_tuyen_qa.json"
    
    # CTU-specific crawler settings
    semaphore_count = 2  # Reduced for CTU politeness
    check_robots_txt = True  # Respect CTU robots.txt
    cache_mode = CacheMode.ENABLED
    output_dir = "output/crawled_ctu_admission_pages"  # Output directory for CTU pages
    
    # Priority filter: 1=highest, 2=medium, 3=lowest (set to 3 to crawl all)
    max_priority = 2  # Only crawl priority 1-2 URLs
    
    # Category filter (leave empty to crawl all categories)
    target_categories = []  # e.g., ['phuong_thuc_xet_tuyen', 'nganh_hoc', 'chi_tieu']
    
    print(f"🎯 Target JSON file: {input_json_file}")
    
    # Check if the specified JSON file exists
    if not Path(input_json_file).exists():
        print(f"❌ JSON file not found: {input_json_file}")
        print(f"💡 Please specify a valid JSON file path in the script")
        return
    
    # Read URLs from the specified JSON file
    try:
        print(f"📄 Reading URLs from: {input_json_file}")
        all_urls = await read_urls_from_json(input_json_file, max_priority, target_categories)
        print(f"✅ Found {len(all_urls)} URLs in the file")
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return
    
    if not all_urls:
        print("❌ No valid URLs found in the JSON file.")
        return
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in all_urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)
    
    if not unique_urls:
        print("❌ No unique URLs found after deduplication.")
        return
    
    print(f"\n🎯 Total unique URLs to crawl: {len(unique_urls)}")
    
    # Show URL preview if not too many
    if len(unique_urls) <= 20:
        print(f"📋 URLs list:")
        for i, url in enumerate(unique_urls, 1):
            print(f"   {i:2d}. {url}")
    else:
        print(f"📋 Sample URLs (showing first 10):")
        for i, url in enumerate(unique_urls[:10], 1):
            print(f"   {i:2d}. {url}")
        print(f"   ... and {len(unique_urls) - 10} more URLs")
    
    try:
        await crawl_urls(
            urls=unique_urls,
            semaphore_count=semaphore_count,
            check_robots_txt=check_robots_txt,
            cache_mode=cache_mode,
            output_dir=output_dir
        )
        
        print(f"\n🎉 CTU Admission Crawling completed!")
        print(f"📁 Results saved in: {output_dir}")
        print(f"📊 Crawled {len(unique_urls)} unique CTU URLs")
        print(f"🎯 Priority filter: ≤ {max_priority}")
        if target_categories:
            print(f"📂 Categories: {', '.join(target_categories)}")
        else:
            print(f"📂 Categories: all")
        print(f"\n💡 Next steps:")
        print(f"   1. Check crawled files in {output_dir}")
        print(f"   2. Run LLM extraction on crawled content")
        print(f"   3. Combine with existing Q&A data")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 