import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import re

async def find_iframe_sources():
    """
    Tìm tất cả iframe sources từ trang CTU
    """
    print("🔍 TÌMNG IFRAME SOURCES")
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        delay_before_return_html=3.0,
        js_code="""
        // Tìm tất cả iframes và in ra console
        console.log('=== SEARCHING FOR IFRAMES ===');
        const iframes = document.querySelectorAll('iframe');
        console.log('Found', iframes.length, 'iframes');
        
        for (let i = 0; i < iframes.length; i++) {
            const iframe = iframes[i];
            console.log('Iframe', i + 1, ':');
            console.log('  src:', iframe.src);
            console.log('  id:', iframe.id);
            console.log('  class:', iframe.className);
            console.log('  name:', iframe.name);
            console.log('  width:', iframe.width);
            console.log('  height:', iframe.height);
            console.log('---');
        }
        
        // Tìm tất cả elements có thuộc tính src
        const elementsWithSrc = document.querySelectorAll('[src]');
        console.log('=== ELEMENTS WITH SRC ===');
        for (let elem of elementsWithSrc) {
            if (elem.tagName.toLowerCase() !== 'img') {
                console.log(elem.tagName, ':', elem.src);
            }
        }
        """,
        simulate_user=True
    )
    
    # Các trang có thể chứa iframe
    test_urls = [
        "https://www.ctu.edu.vn/dao-tao/ctdt-dai-hoc.html",
        "https://www.ctu.edu.vn/dao-tao",
        "https://www.ctu.edu.vn/gioi-thieu/don-vi.html"
    ]
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in test_urls:
            print(f"\n📡 Checking: {url}")
            
            try:
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success and result.html:
                    print(f"✅ Success - HTML length: {len(result.html)}")
                    
                    # Tìm iframe trong HTML
                    iframe_pattern = r'<iframe[^>]*src=["\']([^"\']*)["\'][^>]*>'
                    iframes = re.findall(iframe_pattern, result.html, re.IGNORECASE)
                    
                    if iframes:
                        print(f"🎯 Found {len(iframes)} iframe(s):")
                        for i, iframe_src in enumerate(iframes, 1):
                            print(f"  {i}. {iframe_src}")
                    else:
                        print("❌ No iframes found in HTML")
                    
                    # Tìm các script có thể load iframe động
                    script_pattern = r'<script[^>]*>(.*?)</script>'
                    scripts = re.findall(script_pattern, result.html, re.IGNORECASE | re.DOTALL)
                    
                    potential_urls = []
                    for script in scripts:
                        # Tìm URLs trong JavaScript
                        url_pattern = r'["\']https?://[^"\']*\.php[^"\']*["\']'
                        urls_in_script = re.findall(url_pattern, script)
                        potential_urls.extend(urls_in_script)
                    
                    if potential_urls:
                        print(f"🔗 Potential dynamic URLs found in scripts:")
                        for url in set(potential_urls):  # Remove duplicates
                            clean_url = url.strip('"\'')
                            print(f"  - {clean_url}")
                    
                    # Lưu HTML để debug
                    filename = f"output/debug_{url.split('/')[-1]}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result.html)
                    print(f"💾 HTML saved: {filename}")
                    
                else:
                    print(f"❌ Failed to crawl: {url}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")

async def analyze_page_structure():
    """
    Phân tích cấu trúc trang để hiểu cách iframe được load
    """
    print("\n🔬 ANALYZING PAGE STRUCTURE")
    
    browser_config = BrowserConfig(
        headless=False,  # Visible để có thể debug
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        delay_before_return_html=5.0,
        js_code="""
        // Wait một chút để page load
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Tìm và log tất cả network requests
        const performanceEntries = performance.getEntriesByType('navigation');
        console.log('Navigation entries:', performanceEntries);
        
        const resourceEntries = performance.getEntriesByType('resource');
        console.log('Resource entries count:', resourceEntries.length);
        
        // Lọc các PHP requests
        const phpRequests = resourceEntries.filter(entry => 
            entry.name.includes('.php') || 
            entry.name.includes('subject') ||
            entry.name.includes('branch')
        );
        
        console.log('=== PHP/API REQUESTS ===');
        phpRequests.forEach(req => {
            console.log('URL:', req.name);
            console.log('Type:', req.initiatorType);
            console.log('Duration:', req.duration);
            console.log('---');
        });
        
        // Inspect DOM structure
        console.log('=== DOM STRUCTURE ===');
        const divs = document.querySelectorAll('div[id], div[class*="program"]');
        divs.forEach(div => {
            console.log('Div:', div.id || div.className);
            console.log('innerHTML length:', div.innerHTML.length);
        });
        """,
        simulate_user=True,
        page_timeout=15000
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        url = "https://www.ctu.edu.vn/dao-tao/ctdt-dai-hoc.html"
        print(f"🚀 Analyzing: {url}")
        
        result = await crawler.arun(url=url, config=run_config)
        
        if result.success:
            print("✅ Analysis completed - check browser console for details")
        else:
            print("❌ Analysis failed")

async def main():
    import os
    os.makedirs("output", exist_ok=True)
    
    # Step 1: Find iframes in HTML
    await find_iframe_sources()
    
    # Step 2: Analyze page structure (opens browser)
    print("\n" + "="*50)
    user_input = input("🤔 Do you want to run visual analysis? (y/n): ")
    if user_input.lower() == 'y':
        await analyze_page_structure()

if __name__ == "__main__":
    asyncio.run(main()) 