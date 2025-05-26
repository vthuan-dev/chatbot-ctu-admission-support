import asyncio
import json
import os
from pathlib import Path
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime

def load_urls_from_json(json_file):
    """
    Load URLs from extraction JSON file
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        urls = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            for chunk in data:
                if isinstance(chunk, dict) and 'extracted_urls' in chunk:
                    for url_info in chunk['extracted_urls']:
                        if isinstance(url_info, dict) and 'url' in url_info:
                            urls.append({
                                'url': url_info['url'],
                                'text': url_info.get('text', 'No description'),
                                'category': url_info.get('category', 'unknown'),
                                'priority': url_info.get('priority', 3)
                            })
        elif isinstance(data, dict) and 'extracted_urls' in data:
            for url_info in data['extracted_urls']:
                if isinstance(url_info, dict) and 'url' in url_info:
                    urls.append({
                        'url': url_info['url'],
                        'text': url_info.get('text', 'No description'),
                        'category': url_info.get('category', 'unknown'),
                        'priority': url_info.get('priority', 3)
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
    
    try:
        print(f"🔍 Crawling: {text}")
        print(f"   URL: {url}")
        
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
                f.write(f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(result.markdown)
            
            print(f"✅ Success: {len(result.markdown)} characters")
            print(f"   Saved to: {md_file.name}")
            
            return {
                'url': url,
                'text': text,
                'category': category,
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
                'success': False,
                'error': result.error_message
            }
            
    except Exception as e:
        print(f"❌ Error crawling {url}: {e}")
        return {
            'url': url,
            'text': text,
            'category': category,
            'success': False,
            'error': str(e)
        }

async def main():
    """
    Main function to crawl URLs from JSON files
    """
    print("🚀 Starting URL crawling from JSON files...")
    
    # Find JSON files with URLs
    json_files = [
        "output/https_tuyensinh.ctu.edu.vn_.json",
        "output/ctu_detailed_majors_extracted.json"
    ]
    
    # Add any other JSON files in output directory
    output_dir = Path("output")
    for file in output_dir.glob("*_extracted.json"):
        if str(file) not in json_files:
            json_files.append(str(file))
    
    print(f"📁 Found {len(json_files)} JSON files to check for URLs:")
    for file in json_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (not found)")
    
    # Collect all URLs
    all_urls = []
    for json_file in json_files:
        if not Path(json_file).exists():
            continue
        
        urls = load_urls_from_json(json_file)
        print(f"📝 {Path(json_file).name}: {len(urls)} URLs")
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
    
    # Create output directory
    crawl_output_dir = Path("output/crawled_from_json")
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
        "total_urls": len(unique_urls),
        "successful": len([r for r in results if r['success']]),
        "failed": len([r for r in results if not r['success']]),
        "results": results
    }
    
    summary_file = crawl_output_dir / "crawl_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Show final statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n🎉 Crawling completed!")
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

if __name__ == "__main__":
    asyncio.run(main()) 