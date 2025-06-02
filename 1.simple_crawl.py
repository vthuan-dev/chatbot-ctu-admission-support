import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime
async def main():
    # Configure browser and crawler settings with JavaScript support
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    run_config = CrawlerRunConfig(
        wait_for="css:.content, iframe, table, .program-div-3",  # Wait for dynamic content
        delay_before_return_html=5.0,  # Wait longer for dynamic loading
        js_code="""
        // Function to click and wait for content to load
        async function clickAndWaitForContent() {
            // Try to find and click on different tabs/sections
            const selectors = [
                '.program-div-3',
                '[onclick*="branch"]',
                '[onclick*="subject"]',
                'table tr',
                '.khoa-dao-tao',
                '.nganh-dao-tao'
            ];
            
            for (let selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (let element of elements) {
                    if (element && element.click) {
                        console.log('Clicking:', selector);
                        element.click();
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            }
            
            // Scroll to trigger any lazy loading
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Try to trigger any hidden iframes or dynamic content
            const iframes = document.querySelectorAll('iframe');
            console.log('Found iframes:', iframes.length);
            
            // Look for any data attributes or onclick handlers
            const clickableElements = document.querySelectorAll('[onclick], [data-*]');
            console.log('Found clickable elements:', clickableElements.length);
        }
        
        await clickAndWaitForContent();
        """,
        remove_overlay_elements=True,
        simulate_user=True,
        override_navigator=True,
        page_timeout=30000  # Increase timeout for dynamic content
    )
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Set the URL you want to crawl - use admission site with real content
        url = "https://tuyensinh.ctu.edu.vn/"
        print(f"🎯 Crawling: {url}")
        
        # Run the crawler
        result = await crawler.arun(url=url, config=run_config)
        
        # Display results
        print(f"✅ Crawl successful: {result.success}")
        print(f"📊 Status code: {result.status_code}")
        print(f"📄 Content length: {len(result.markdown) if result.markdown else 0} characters")
        
        if result.success and result.markdown:
            # Create the output directory if it doesn't exist
            import os
            os.makedirs("output", exist_ok=True)
            
            # Save the result to a file in the output directory
            with open("output/crawl_result.md", "w", encoding="utf-8") as f:
                f.write(result.markdown)
            
            print(f"💾 Saved to: output/crawl_result.md")
            
            # Show preview of content
            print("\n--- Content Preview (first 1000 chars) ---")
            preview = result.markdown[:1000]
            print(preview)
            if len(result.markdown) > 1000:
                print("... (truncated)")
                
            # Check for key content indicators
            content_checks = {
                "Khoa": "Khoa" in result.markdown,
                "Ngành": "ngành" in result.markdown.lower(),
                "Đào tạo": "đào tạo" in result.markdown.lower(),
                "JavaScript iframe": "không hỗ trợ khung nội tuyến" in result.markdown
            }
            
            print(f"\n🔍 Content Analysis:")
            for check, found in content_checks.items():
                status = "✅" if found else "❌"
                print(f"  {status} {check}: {found}")
                
        else:
            print(f"❌ Crawl failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            
        # Show HTML structure for debugging
        if result.html:
            print(f"\n🔧 Raw HTML length: {len(result.html)} characters")
            print("--- HTML Structure Preview ---")
            print(result.html[:800] + "..." if len(result.html) > 800 else result.html)

if __name__ == "__main__":
    asyncio.run(main()) 