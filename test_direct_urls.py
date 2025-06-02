import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def test_direct_content_urls():
    """
    Test các URL có thể chứa nội dung thực tế dựa trên patterns
    """
    print("🎯 TESTING DIRECT CONTENT URLs")
    
    # Các URL có thể chứa nội dung thật
    potential_urls = [
        # Base directories
        "https://www.ctu.edu.vn/dao-tao/",
        "https://www.ctu.edu.vn/webctu_program/",
        
        # Possible direct content pages
        "https://www.ctu.edu.vn/dao-tao/subject.php",
        "https://www.ctu.edu.vn/dao-tao/branch.php",
        "https://www.ctu.edu.vn/webctu_program/subject.php",
        "https://www.ctu.edu.vn/webctu_program/branch.php",
        
        # Alternative patterns
        "https://www.ctu.edu.vn/gioi-thieu/don-vi/",
        "https://www.ctu.edu.vn/gioi-thieu/don-vi.html",
        
        # Admission sites (known to work)
        "https://tuyensinh.ctu.edu.vn/",
        "https://tuyensinh.ctu.edu.vn/nganh-va-chi-tieu",
        "https://tuyensinh.ctu.edu.vn/chuong-trinh-dao-tao",
    ]
    
    browser_config = BrowserConfig(headless=True, verbose=True)
    run_config = CrawlerRunConfig(
        delay_before_return_html=2.0,
        simulate_user=True
    )
    
    results = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url in enumerate(potential_urls, 1):
            print(f"\n📡 [{i}/{len(potential_urls)}] Testing: {url}")
            
            try:
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success and result.markdown:
                    content_length = len(result.markdown)
                    
                    # Check content quality
                    content_lower = result.markdown.lower()
                    quality_indicators = [
                        'ngành', 'khoa', 'đào tạo', 'chuyên ngành',
                        'mã ngành', 'tuyển sinh', 'học phí'
                    ]
                    
                    quality_score = sum(1 for indicator in quality_indicators if indicator in content_lower)
                    has_real_content = quality_score >= 3 and content_length > 1000
                    
                    status = "🎯 GOOD" if has_real_content else "⚠️  BASIC"
                    print(f"  {status} - Length: {content_length:,} chars, Quality: {quality_score}/7")
                    
                    # Preview content
                    if has_real_content:
                        print(f"  📋 Preview: {result.markdown[:200]}...")
                    
                    results.append({
                        'url': url,
                        'length': content_length,
                        'quality_score': quality_score,
                        'has_real_content': has_real_content,
                        'content': result.markdown
                    })
                    
                else:
                    print(f"  ❌ FAILED - Status: {result.status_code if hasattr(result, 'status_code') else 'Unknown'}")
                    
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
    
    # Analyze results
    print(f"\n📊 RESULTS SUMMARY:")
    good_sources = [r for r in results if r['has_real_content']]
    basic_sources = [r for r in results if not r['has_real_content'] and r['length'] > 0]
    
    print(f"🎯 Good content sources: {len(good_sources)}")
    print(f"⚠️  Basic sources: {len(basic_sources)}")
    
    if good_sources:
        print(f"\n🌟 TOP CONTENT SOURCES:")
        # Sort by quality and length
        good_sources.sort(key=lambda x: (x['quality_score'], x['length']), reverse=True)
        
        for i, source in enumerate(good_sources[:5], 1):
            print(f"  {i}. {source['url']}")
            print(f"     📊 Quality: {source['quality_score']}/7, Length: {source['length']:,} chars")
        
        # Save best content
        best_source = good_sources[0]
        with open("output/best_crawl_result.md", "w", encoding="utf-8") as f:
            f.write(f"# Best Content Source\n")
            f.write(f"URL: {best_source['url']}\n")
            f.write(f"Quality Score: {best_source['quality_score']}/7\n")
            f.write(f"Length: {best_source['length']:,} characters\n\n")
            f.write(best_source['content'])
        
        print(f"\n💾 Saved best content to: output/best_crawl_result.md")
        print(f"🔧 You can now run: python 2.llm_extract.py")
        
        return best_source['url']
    
    else:
        print("\n❌ No good content sources found")
        return None

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    
    asyncio.run(test_direct_content_urls()) 