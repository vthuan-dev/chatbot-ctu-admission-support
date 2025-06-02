import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv
from bs4 import BeautifulSoup


class CTUKnowledgeCrawler:
    """Crawler for CTU admission knowledge base"""
    
    def __init__(self):
        self.knowledge_base = {
            "metadata": {
                "version": "1.0",
                "crawled_date": datetime.now().isoformat(),
                "university": "Can Tho University",
                "academic_year": "2025"
            },
            "data": {
                "programs": [],
                "admission_methods": [],
                "facilities": [],
                "contact_info": {},
                "scholarships": []
            }
        }
        
        # Define crawl targets
        self.crawl_targets = {
            "programs": [
                "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/841-danh-muc-nganh-va-chi-tieu-tuyen-sinh-dhcq.html",
                "https://tuyensinh.ctu.edu.vn/dai-hoc-chinh-quy/chuong-trinh-chat-luong-cao.html",
                "https://tuyensinh.ctu.edu.vn/dai-hoc-chinh-quy/chuong-trinh-tien-tien.html"
            ],
            "admission_methods": [
                "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/943-phuong-thuc-xet-tuyen.html"
            ],
            "facilities": [
                "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/897-ky-tuc-xa.html",
                "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/898-khu-hoa-an.html"
            ]
        }
    
    async def crawl_page(self, url: str) -> str:
        """Crawl a single page and return markdown content"""
        try:
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1200,
                viewport_height=800
            )
            
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                wait_for="body",
                delay_before_return_html=2.0,
                excluded_tags=['nav', 'footer', 'header'],
                remove_overlay_elements=True
            )
            
            print(f"🕷️ Crawling: {url}")
            
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    browser_config=browser_config,
                    crawl_config=crawl_config
                )
                
                if result.success:
                    print(f"✅ Successfully crawled: {url}")
                    return result.markdown
                else:
                    print(f"❌ Failed to crawl: {url}")
                    return ""
                    
        except Exception as e:
            print(f"❌ Error crawling {url}: {e}")
            return ""
    
    def extract_programs_info(self, markdown_content: str, url: str) -> List[Dict]:
        """Extract program information from markdown"""
        programs = []
        
        # Pattern matching for program info
        # This is a simplified example - adjust based on actual content structure
        lines = markdown_content.split('\n')
        current_program = {}
        
        for line in lines:
            line = line.strip()
            
            # Look for program codes (7-digit numbers)
            if len(line) >= 7 and line[:7].isdigit():
                if current_program:
                    programs.append(current_program)
                current_program = {"program_code": line[:7]}
            
            # Extract other info based on keywords
            if current_program:
                if "học phí" in line.lower():
                    current_program["tuition_fee"] = line
                elif "thời gian" in line.lower():
                    current_program["duration"] = line
                elif "chỉ tiêu" in line.lower():
                    current_program["quota"] = line
        
        if current_program:
            programs.append(current_program)
        
        return programs
    
    def extract_admission_methods(self, markdown_content: str) -> List[Dict]:
        """Extract admission methods information"""
        methods = []
        
        # Common admission methods at CTU
        method_keywords = {
            "xét tuyển điểm thi THPT": "THPT_EXAM",
            "xét tuyển học bạ": "ACADEMIC_RECORD", 
            "xét tuyển V-SAT": "VSAT_TEST",
            "xét tuyển thẳng": "DIRECT_ADMISSION",
            "xét tuyển kết hợp": "COMBINED",
            "xét tuyển năng lực": "APTITUDE_TEST"
        }
        
        for keyword, method_id in method_keywords.items():
            if keyword in markdown_content.lower():
                methods.append({
                    "method_id": method_id,
                    "method_name": keyword,
                    "description": f"Phương thức {keyword} tại CTU"
                })
        
        return methods
    
    def extract_facilities_info(self, markdown_content: str, facility_type: str) -> Dict:
        """Extract facility information"""
        facility = {
            "type": facility_type,
            "details": {}
        }
        
        # Extract based on common patterns
        if "địa chỉ" in markdown_content.lower():
            # Extract address
            pass
        
        if "sức chứa" in markdown_content.lower() or "phòng" in markdown_content.lower():
            # Extract capacity
            pass
        
        if "liên hệ" in markdown_content.lower():
            # Extract contact
            pass
        
        return facility
    
    async def crawl_all(self):
        """Crawl all target URLs and build knowledge base"""
        
        print("🚀 Starting CTU Knowledge Base Crawling...")
        
        # Crawl programs
        print("\n📚 Crawling program information...")
        for url in self.crawl_targets["programs"]:
            content = await self.crawl_page(url)
            if content:
                programs = self.extract_programs_info(content, url)
                self.knowledge_base["data"]["programs"].extend(programs)
                await asyncio.sleep(2)  # Be polite
        
        # Crawl admission methods
        print("\n🎯 Crawling admission methods...")
        for url in self.crawl_targets["admission_methods"]:
            content = await self.crawl_page(url)
            if content:
                methods = self.extract_admission_methods(content)
                self.knowledge_base["data"]["admission_methods"].extend(methods)
                await asyncio.sleep(2)
        
        # Crawl facilities
        print("\n🏫 Crawling facility information...")
        for url in self.crawl_targets["facilities"]:
            content = await self.crawl_page(url)
            if content:
                facility_type = "dormitory" if "ktx" in url.lower() else "campus"
                facility = self.extract_facilities_info(content, facility_type)
                self.knowledge_base["data"]["facilities"].append(facility)
                await asyncio.sleep(2)
        
        # Add static contact info (can be updated with crawled data)
        self.knowledge_base["data"]["contact_info"] = {
            "hotline": "0292 3872 728",
            "email": "tuyensinh@ctu.edu.vn",
            "website": "https://tuyensinh.ctu.edu.vn",
            "facebook": "https://www.facebook.com/ctu.tvts",
            "address": "Khu II, đường 3/2, P. Xuân Khánh, Q. Ninh Kiều, TP. Cần Thơ"
        }
        
        print("\n✅ Crawling completed!")
        
    def save_knowledge_base(self, output_dir: str = "output/knowledge_base"):
        """Save the knowledge base to JSON file"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Main knowledge base file
        kb_file = output_path / "ctu_knowledge_base.json"
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
        
        # Create separate files for each data type
        for data_type, data in self.knowledge_base["data"].items():
            if data:  # Only save non-empty data
                file_path = output_path / f"ctu_{data_type}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "type": data_type,
                        "data": data,
                        "updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
        
        # Generate statistics
        stats = {
            "crawl_date": datetime.now().isoformat(),
            "statistics": {
                "programs": len(self.knowledge_base["data"]["programs"]),
                "admission_methods": len(self.knowledge_base["data"]["admission_methods"]),
                "facilities": len(self.knowledge_base["data"]["facilities"]),
                "total_items": sum(len(v) if isinstance(v, list) else 1 
                                 for v in self.knowledge_base["data"].values())
            }
        }
        
        stats_file = output_path / "crawl_statistics.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 Knowledge Base Statistics:")
        for key, value in stats["statistics"].items():
            print(f"   - {key}: {value}")
        print(f"\n💾 Saved to: {kb_file}")


async def main():
    """Main function to run the knowledge crawler"""
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Initialize crawler
    crawler = CTUKnowledgeCrawler()
    
    # Crawl all data
    await crawler.crawl_all()
    
    # Save results
    crawler.save_knowledge_base()
    
    print("\n🎉 Knowledge base crawling completed!")


if __name__ == "__main__":
    asyncio.run(main()) 