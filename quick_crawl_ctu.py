import asyncio
import os
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime

async def crawl_ctu_admission_sites():
    """
    Crawl các trang tuyển sinh CTU có thông tin sẵn có (không cần dynamic loading)
    """
    print("🚀 CRAWL CTU ADMISSION SITES")
    
    # Danh sách URLs tuyển sinh CTU với thông tin tĩnh
    ctu_urls = [
        {
            'url': 'https://tuyensinh.ctu.edu.vn/',
            'name': 'Trang chủ tuyển sinh',
            'priority': 1
        },
        {
            'url': 'https://tuyensinh.ctu.edu.vn/nganh-va-chi-tieu',
            'name': 'Ngành và chỉ tiêu',
            'priority': 1
        },
        {
            'url': 'https://tuyensinh.ctu.edu.vn/chuong-trinh-dao-tao',
            'name': 'Chương trình đào tạo',
            'priority': 1
        },
        {
            'url': 'https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen',
            'name': 'Phương thức xét tuyển',
            'priority': 1
        },
        {
            'url': 'https://tuyensinh.ctu.edu.vn/hoc-phi',
            'name': 'Học phí',
            'priority': 1
        },
        {
            'url': 'https://www.ctu.edu.vn/dao-tao',
            'name': 'Đào tạo CTU',
            'priority': 2
        },
        {
            'url': 'https://ctc.ctu.edu.vn/',
            'name': 'Chương trình chất lượng cao',
            'priority': 2
        }
    ]
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        delay_before_return_html=2.0,
        simulate_user=True,
        remove_overlay_elements=True
    )
    
    os.makedirs("output", exist_ok=True)
    all_content = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url_info in enumerate(ctu_urls, 1):
            try:
                url = url_info['url']
                name = url_info['name']
                priority = url_info['priority']
                
                print(f"📡 [{i}/{len(ctu_urls)}] {name}")
                print(f"    🌐 {url}")
                
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success and result.markdown:
                    content_length = len(result.markdown)
                    print(f"    ✅ Success: {content_length:,} chars")
                    
                    # Check content quality
                    content_lower = result.markdown.lower()
                    quality_indicators = [
                        'ngành', 'tuyển sinh', 'đào tạo', 'học phí', 
                        'chỉ tiêu', 'phương thức', 'xét tuyển'
                    ]
                    
                    quality_score = sum(1 for indicator in quality_indicators if indicator in content_lower)
                    print(f"    📊 Quality score: {quality_score}/{len(quality_indicators)}")
                    
                    content_info = {
                        'url': url,
                        'name': name,
                        'priority': priority,
                        'content': result.markdown,
                        'length': content_length,
                        'quality_score': quality_score,
                        'timestamp': datetime.now().isoformat()
                    }
                    all_content.append(content_info)
                    
                    # Save individual file
                    safe_name = name.replace(' ', '_').replace('/', '_')
                    individual_file = f"output/ctu_{priority}_{safe_name}.md"
                    with open(individual_file, 'w', encoding='utf-8') as f:
                        f.write(f"# {name}\n")
                        f.write(f"URL: {url}\n")
                        f.write(f"Crawled: {datetime.now()}\n")
                        f.write(f"Quality Score: {quality_score}/{len(quality_indicators)}\n\n")
                        f.write(result.markdown)
                    
                else:
                    print(f"    ❌ Failed: {url}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    # Combine all content based on priority
    if all_content:
        # Sort by priority (1 = highest) then by quality score
        all_content.sort(key=lambda x: (x['priority'], -x['quality_score']))
        
        combined_markdown = f"# CTU ADMISSION CRAWL RESULTS\n"
        combined_markdown += f"Generated: {datetime.now()}\n"
        combined_markdown += f"Total sources: {len(all_content)}\n\n"
        
        # Add summary
        combined_markdown += "## SUMMARY\n\n"
        for content_info in all_content:
            combined_markdown += f"- **{content_info['name']}** (Priority {content_info['priority']})\n"
            combined_markdown += f"  - Quality: {content_info['quality_score']}/7\n"
            combined_markdown += f"  - Length: {content_info['length']:,} chars\n"
            combined_markdown += f"  - URL: {content_info['url']}\n\n"
        
        combined_markdown += "\n---\n\n"
        
        # Add content with priority 1 first
        high_priority_content = [c for c in all_content if c['priority'] == 1]
        medium_priority_content = [c for c in all_content if c['priority'] == 2]
        
        for content_group, group_name in [(high_priority_content, "HIGH PRIORITY"), (medium_priority_content, "MEDIUM PRIORITY")]:
            if content_group:
                combined_markdown += f"# {group_name} CONTENT\n\n"
                
                for content_info in content_group:
                    combined_markdown += f"## {content_info['name']}\n"
                    combined_markdown += f"**URL:** {content_info['url']}\n"
                    combined_markdown += f"**Quality Score:** {content_info['quality_score']}/7\n"
                    combined_markdown += f"**Crawled:** {content_info['timestamp']}\n\n"
                    combined_markdown += content_info['content']
                    combined_markdown += "\n\n---\n\n"
        
        # Save combined file
        combined_file = "output/ctu_admission_combined.md"
        with open(combined_file, "w", encoding="utf-8") as f:
            f.write(combined_markdown)
        
        print(f"\n🎊 CRAWL COMPLETED!")
        print(f"📄 Combined file: {combined_file}")
        print(f"📊 Total content: {len(combined_markdown):,} characters")
        print(f"🎯 High priority sources: {len(high_priority_content)}")
        print(f"📝 Medium priority sources: {len(medium_priority_content)}")
        
        # Display top quality sources
        print(f"\n🌟 TOP QUALITY SOURCES:")
        top_sources = sorted(all_content, key=lambda x: -x['quality_score'])[:3]
        for i, source in enumerate(top_sources, 1):
            print(f"  {i}. {source['name']} (Score: {source['quality_score']}/7)")
            print(f"     📏 {source['length']:,} chars - {source['url']}")
        
        print(f"\n🔧 NEXT STEP:")
        print(f"   python 2.llm_extract.py")
        print(f"   (Sẽ sử dụng file: {combined_file})")
        
        return combined_file
    
    return None

if __name__ == "__main__":
    asyncio.run(crawl_ctu_admission_sites()) 