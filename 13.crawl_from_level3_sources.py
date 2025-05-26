import asyncio
import json
import os
from pathlib import Path
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime

def load_urls_from_level3_json(json_file):
    """
    Load URLs from Level 3 extraction JSON file (from source field in Q&A pairs)
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        urls = []
        
        # Extract URLs from source field in Q&A pairs
        if isinstance(data, dict) and 'qa_pairs' in data:
            for qa in data['qa_pairs']:
                if isinstance(qa, dict) and 'source' in qa:
                    source_url = qa['source']
                    if source_url and source_url.startswith('http'):
                        urls.append({
                            'url': source_url,
                            'text': qa.get('question', 'No description')[:100],
                            'category': qa.get('category', 'unknown'),
                            'priority': qa.get('priority', 3),
                            'from_file': Path(json_file).name
                        })
        
        return urls
    except Exception as e:
        print(f"⚠️ Error loading URLs from {json_file}: {e}")
        return []

async def crawl_url(crawler, url_info, output_dir):
    """
    Crawl a single URL and save the result
    """
    url = url_info['url']
    text = url_info['text']
    category = url_info['category']
    from_file = url_info['from_file']
    
    try:
        print(f"🔍 Crawling: {text}")
        print(f"   URL: {url}")
        print(f"   From: {from_file}")
        
        # Configure crawler run
        run_config = CrawlerRunConfig()
        
        # Run the crawler
        result = await crawler.arun(url=url, config=run_config)
        
        if result.success:
            # Create filename from URL
            url_filename = url.replace("://", "_").replace("/", "_").replace("?", "_").replace("=", "_")
            if len(url_filename) > 150:
                url_filename = url_filename[:150]
            
            # Save markdown content
            md_file = output_dir / f"{url_filename}.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(f"# {text}\n\n")
                f.write(f"**URL:** {url}\n")
                f.write(f"**Category:** {category}\n")
                f.write(f"**Source File:** {from_file}\n")
                f.write(f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(result.markdown)
            
            print(f"✅ Success: {len(result.markdown)} characters")
            print(f"   Saved to: {md_file.name}")
            
            return {
                'url': url,
                'text': text,
                'category': category,
                'from_file': from_file,
                'success': True,
                'content_length': len(result.markdown),
                'file': str(md_file)
            }
        else:
            print(f"❌ Failed: {result.error_message}")
            return {
                'url': url,
                'text': text,
                'category': category,
                'from_file': from_file,
                'success': False,
                'error': result.error_message
            }
            
    except Exception as e:
        print(f"❌ Error crawling {url}: {e}")
        return {
            'url': url,
            'text': text,
            'category': category,
            'from_file': from_file,
            'success': False,
            'error': str(e)
        }

async def main():
    """
    Main function to crawl URLs from Level 3 extracted JSON files and save to Level 4
    """
    print("🚀 Starting URL crawling from Level 3 extracted files...")
    print("📁 Results will be saved to Level 4 folder")
    
    # Find all JSON files in extracted_level3 folder
    level3_dir = Path("output/extracted_level3")
    if not level3_dir.exists():
        print(f"❌ Directory {level3_dir} not found!")
        return
    
    json_files = list(level3_dir.glob("*.json"))
    # Exclude the combined file
    json_files = [f for f in json_files if "combined" not in f.name]
    
    print(f"📁 Found {len(json_files)} JSON files in extracted_level3:")
    for file in json_files:
        print(f"   ✅ {file.name}")
    
    # Collect all URLs from source fields
    all_urls = []
    for json_file in json_files:
        urls = load_urls_from_level3_json(json_file)
        print(f"📝 {json_file.name}: {len(urls)} URLs from sources")
        all_urls.extend(urls)
    
    # Remove duplicates based on URL
    unique_urls = []
    seen_urls = set()
    for url_info in all_urls:
        url = url_info['url']
        if url not in seen_urls:
            seen_urls.add(url)
            unique_urls.append(url_info)
    
    print(f"\n📊 URL Statistics:")
    print(f"   🔗 Total URLs found: {len(all_urls)}")
    print(f"   🔄 Unique URLs: {len(unique_urls)}")
    print(f"   ❌ Duplicates removed: {len(all_urls) - len(unique_urls)}")
    
    if not unique_urls:
        print("❌ No URLs found to crawl!")
        return
    
    # Sort by priority (1 = highest priority)
    unique_urls.sort(key=lambda x: x['priority'])
    
    # Show URLs to be crawled
    print(f"\n🔗 URLs to crawl (sorted by priority):")
    for i, url_info in enumerate(unique_urls[:10], 1):
        print(f"   {i}. Priority {url_info['priority']}: {url_info['url']}")
        print(f"      From: {url_info['from_file']}")
    if len(unique_urls) > 10:
        print(f"   ... and {len(unique_urls) - 10} more URLs")
    
    # Create Level 4 output directory
    crawl_output_dir = Path("output/crawled_pages_level4")
    crawl_output_dir.mkdir(exist_ok=True, parents=True)
    
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Start crawling
    print(f"\n🔍 Starting to crawl {len(unique_urls)} unique URLs...")
    print(f"📁 Results will be saved in: {crawl_output_dir}")
    
    results = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url_info in enumerate(unique_urls, 1):
            print(f"\n📄 [{i}/{len(unique_urls)}] Priority {url_info['priority']}")
            
            result = await crawl_url(crawler, url_info, crawl_output_dir)
            results.append(result)
            
            # Small delay to be respectful
            await asyncio.sleep(1)
    
    # Save crawling summary
    summary = {
        "crawl_date": datetime.now().isoformat(),
        "source": "Level 3 extracted JSON files",
        "level": "Level 4",
        "total_urls": len(unique_urls),
        "successful": len([r for r in results if r['success']]),
        "failed": len([r for r in results if not r['success']]),
        "results": results
    }
    
    summary_file = crawl_output_dir / "level4_crawl_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Show final statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n🎉 Level 4 Crawling completed!")
    print(f"📊 Final Statistics:")
    print(f"   ✅ Successful: {len(successful)}")
    print(f"   ❌ Failed: {len(failed)}")
    print(f"   📁 Files saved in: {crawl_output_dir}")
    print(f"   📄 Summary: {summary_file}")
    
    if successful:
        total_content = sum(r['content_length'] for r in successful)
        print(f"   📝 Total content: {total_content:,} characters")
        
        print(f"\n📝 Sample successful crawls:")
        for result in successful[:5]:
            print(f"   ✅ {result['text'][:50]}... ({result['content_length']:,} chars)")
    
    if failed:
        print(f"\n❌ Failed URLs:")
        for result in failed[:3]:
            print(f"   ❌ {result['text'][:50]}... - {result.get('error', 'Unknown error')}")
    
    print(f"\n💡 Next step: Extract Q&A from Level 4 markdown files!")
    print(f"💡 You can use 11.extract_from_markdown.py on the new Level 4 folder")

if __name__ == "__main__":
    asyncio.run(main()) 