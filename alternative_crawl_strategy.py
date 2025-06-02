import asyncio
import json
import aiohttp
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime

async def strategy_1_api_direct():
    """
    Chiến lược 1: Gọi trực tiếp API endpoints với POST requests
    Dựa trên phân tích DevTools, các API này cần POST requests
    """
    print("🎯 CHIẾN LƯỢC 1: GỌI TRỰC TIẾP API (POST REQUESTS)")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.ctu.edu.vn/dao-tao/ctdt-dai-hoc.html',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.ctu.edu.vn',
        'Connection': 'keep-alive'
    }
    
    # API endpoints với POST data dự đoán từ structure
    api_calls = [
        {
            'url': 'https://www.ctu.edu.vn/dao-tao/subject.php',
            'data': {},  # Empty POST để thử
            'description': 'Get subjects/departments'
        },
        {
            'url': 'https://www.ctu.edu.vn/dao-tao/branch.php', 
            'data': {},  # Empty POST để thử
            'description': 'Get branches/programs'
        },
        {
            'url': 'https://www.ctu.edu.vn/webctu_program/subject.php',
            'data': {},
            'description': 'Alternative subject endpoint'
        }
    ]
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for api_call in api_calls:
            try:
                print(f"📡 POST Request: {api_call['url']}")
                print(f"📝 Description: {api_call['description']}")
                
                # Thử POST request
                async with session.post(api_call['url'], data=api_call['data']) as response:
                    content = await response.text()
                    print(f"  ✅ Status: {response.status}")
                    print(f"  📄 Content length: {len(content)}")
                    print(f"  📋 Content preview: {content[:300]}...")
                    
                    # Lưu kết quả
                    filename = f"output/api_post_{api_call['url'].split('/')[-1]}"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  💾 Saved: {filename}\n")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}\n")
                
        # Thử thêm với một số parameters có thể
        print("🔬 Thử với parameters dự đoán...")
        potential_params = [
            {'khoa': '1'},  # Khoa ID
            {'nganh': '1'}, # Ngành ID  
            {'type': 'all'},
            {'action': 'get_data'},
        ]
        
        for params in potential_params:
            try:
                print(f"📡 POST với params: {params}")
                async with session.post('https://www.ctu.edu.vn/dao-tao/subject.php', data=params) as response:
                    content = await response.text()
                    if len(content) > 50:  # Có data thực tế
                        print(f"  🎯 SUCCESS with params {params}!")
                        print(f"  📄 Content length: {len(content)}")
                        filename = f"output/api_success_{str(params).replace(' ', '_')}.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"  💾 Saved: {filename}")
                    else:
                        print(f"  ❌ Empty response with params {params}")
            except Exception as e:
                print(f"  ❌ Error with {params}: {e}")

async def strategy_2_selenium_simulation():
    """
    Chiến lược 2: Selenium-like interaction để trigger API calls
    """
    print("🎯 CHIẾN LƯỢC 2: SIMULATION CLICK EVENTS")
    
    browser_config = BrowserConfig(
        headless=False,  # Chạy visible để debug
        verbose=True
    )
    
    run_config = CrawlerRunConfig(
        wait_for="css:.program-div-3, table",
        delay_before_return_html=3.0,
        js_code="""
        // Hàm tìm và click tất cả clickable elements
        async function triggerAllClicks() {
            console.log('🔍 Finding clickable elements...');
            
            // Tìm tất cả elements có onclick
            const clickables = document.querySelectorAll('[onclick]');
            console.log('Found onclick elements:', clickables.length);
            
            for (let i = 0; i < clickables.length; i++) {
                const element = clickables[i];
                console.log('Clicking element:', i, element.tagName, element.onclick);
                
                try {
                    element.click();
                    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s
                } catch (e) {
                    console.log('Click error:', e);
                }
            }
            
            // Tìm các button, link khác
            const buttons = document.querySelectorAll('button, .btn, [role="button"]');
            console.log('Found buttons:', buttons.length);
            
            for (let button of buttons) {
                try {
                    button.click();
                    await new Promise(resolve => setTimeout(resolve, 1500));
                } catch (e) {
                    console.log('Button click error:', e);
                }
            }
            
            // Scroll để trigger lazy loading
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
        
        await triggerAllClicks();
        """,
        page_timeout=60000,  # 60 giây
        simulate_user=True,
        override_navigator=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        url = "https://www.ctu.edu.vn/dao-tao/ctdt-dai-hoc.html"
        print(f"🚀 Crawling with interaction: {url}")
        
        result = await crawler.arun(url=url, config=run_config)
        
        if result.success:
            with open("output/interactive_crawl.md", "w", encoding="utf-8") as f:
                f.write(result.markdown)
            print(f"✅ Interactive crawl saved: {len(result.markdown)} chars")
        else:
            print(f"❌ Interactive crawl failed")

async def strategy_3_multiple_endpoints():
    """
    Chiến lược 3: Crawl nhiều endpoints khác nhau của CTU
    """
    print("🎯 CHIẾN LƯỢC 3: CRAWL MULTIPLE CTU ENDPOINTS")
    
    # Danh sách URLs có thể có thông tin ngành học
    ctu_urls = [
        "https://tuyensinh.ctu.edu.vn/",  # Trang tuyển sinh chính
        "https://tuyensinh.ctu.edu.vn/nganh-va-chi-tieu",
        "https://tuyensinh.ctu.edu.vn/chuong-trinh-dao-tao",
        "https://www.ctu.edu.vn/dao-tao",
        "https://www.ctu.edu.vn/gioi-thieu/don-vi",
        "https://ctc.ctu.edu.vn/",  # Chương trình chất lượng cao
        "https://gs.ctu.edu.vn/"   # Sau đại học
    ]
    
    browser_config = BrowserConfig(headless=True, verbose=True)
    run_config = CrawlerRunConfig(
        delay_before_return_html=3.0,
        simulate_user=True
    )
    
    all_content = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url in enumerate(ctu_urls, 1):
            try:
                print(f"📡 [{i}/{len(ctu_urls)}] Crawling: {url}")
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success and result.markdown:
                    content_info = {
                        'url': url,
                        'content': result.markdown,
                        'length': len(result.markdown),
                        'timestamp': datetime.now().isoformat()
                    }
                    all_content.append(content_info)
                    print(f"  ✅ Success: {len(result.markdown)} chars")
                else:
                    print(f"  ❌ Failed: {url}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    # Combine all content
    if all_content:
        combined_markdown = f"# CTU COMBINED CRAWL RESULTS - {datetime.now()}\n\n"
        
        for content_info in all_content:
            combined_markdown += f"## Source: {content_info['url']}\n"
            combined_markdown += f"Length: {content_info['length']} characters\n"
            combined_markdown += f"Crawled: {content_info['timestamp']}\n\n"
            combined_markdown += content_info['content']
            combined_markdown += "\n\n---\n\n"
        
        with open("output/ctu_combined_crawl.md", "w", encoding="utf-8") as f:
            f.write(combined_markdown)
        
        print(f"✅ Combined crawl saved: {len(combined_markdown)} chars from {len(all_content)} sources")
        return combined_markdown
    
    return None

async def main():
    """
    Chạy tất cả chiến lược crawling
    """
    import os
    os.makedirs("output", exist_ok=True)
    
    print("🚀 BẮT ĐẦU CRAWL CTU VỚI MULTIPLE STRATEGIES\n")
    
    # Chiến lược 1: API Direct
    await strategy_1_api_direct()
    
    print("\n" + "="*50 + "\n")
    
    # Chiến lược 2: Interactive Simulation  
    await strategy_2_selenium_simulation()
    
    print("\n" + "="*50 + "\n")
    
    # Chiến lược 3: Multiple Endpoints (RECOMMENDED)
    combined_content = await strategy_3_multiple_endpoints()
    
    if combined_content:
        print(f"\n🎊 THÀNH CÔNG! Đã thu thập được {len(combined_content)} ký tự")
        print("📝 Khuyến nghị: Sử dụng file 'ctu_combined_crawl.md' để extract Q&A")
        print("🔧 Chạy tiếp: python 2.llm_extract.py")

if __name__ == "__main__":
    asyncio.run(main()) 