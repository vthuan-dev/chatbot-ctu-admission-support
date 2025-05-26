import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Set, Dict
import time

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv

class AutoRecursiveCTUCrawler:
    """
    🤖 Fully Automated Recursive CTU Crawler
    
    Workflow:
    1. Start with initial URL
    2. Crawl → Convert to .md → Extract to JSON
    3. Find new URLs in JSON
    4. Crawl new URLs → Extract → Find more URLs
    5. Continue until no new URLs or max depth reached
    6. Organize by intent automatically
    7. You can rest! 😴
    """
    
    def __init__(self, api_key: str, max_depth: int = 5, max_urls_per_level: int = 10):
        self.api_key = api_key
        self.max_depth = max_depth
        self.max_urls_per_level = max_urls_per_level
        
        # Tracking
        self.crawled_urls: Set[str] = set()
        self.all_qa_pairs: List[Dict] = []
        self.intent_data: Dict[str, List] = {
            # Core admission intents
            'hoi_nganh_hoc': [],                    # Ngành học, chuyên ngành
            'hoi_phuong_thuc_xet_tuyen': [],       # Phương thức xét tuyển
            'hoi_hoc_phi': [],                     # Học phí, chi phí
            'hoi_lien_he': [],                     # Liên hệ, địa chỉ
            
            # Extended admission intents
            'hoi_diem_chuan': [],                  # Điểm chuẩn, điểm xét tuyển
            'hoi_ho_so_xet_tuyen': [],            # Hồ sơ xét tuyển, thủ tục
            'hoi_lich_tuyen_sinh': [],            # Lịch tuyển sinh, thời gian
            'hoi_hoc_bong': [],                   # Học bổng, hỗ trợ tài chính
            'hoi_co_so_vat_chat': [],             # Cơ sở vật chất, ký túc xá
            'hoi_sinh_vien_quoc_te': [],          # Sinh viên quốc tế
            'hoi_chuong_trinh_lien_ket': [],      # Chương trình liên kết
            'hoi_thuc_tap_viec_lam': [],          # Thực tập, việc làm sau tốt nghiệp
            'hoi_hoat_dong_sinh_vien': [],        # Hoạt động sinh viên, CLB
            'hoi_dao_tao_sau_dai_hoc': [],        # Đào tạo sau đại học
            'hoi_thong_tin_chung': []             # Thông tin chung khác
        }
        
        # Setup directories
        self.setup_directories()
        
    def setup_directories(self):
        """Setup output directories"""
        directories = [
            'output/auto_recursive',
            'output/auto_recursive/markdown',
            'output/auto_recursive/json',
            'output/auto_recursive/by_intent',
            'data/auto_recursive'
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def is_valid_ctu_url(self, url: str) -> bool:
        """Check if URL is valid CTU admission related"""
        if not url or not isinstance(url, str):
            return False
            
        # Must contain CTU indicators
        ctu_indicators = ['ctu.edu.vn', 'tuyensinh', 'nganh', 'hoc-phi', 'xet-tuyen']
        if not any(indicator in url.lower() for indicator in ctu_indicators):
            return False
            
        # Skip unwanted file types
        skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
            
        # Skip already crawled
        if url in self.crawled_urls:
            return False
            
        return True
    
    def detect_intent(self, question: str, answer: str) -> str:
        """Smart intent detection based on keywords"""
        text = (question + " " + answer).lower()
        
        # Enhanced intent keyword mapping
        intent_keywords = {
            # Core admission intents
            'hoi_nganh_hoc': ['ngành', 'chuyên ngành', 'đào tạo', 'chương trình', 'major', 'faculty', 'khoa', 'bộ môn'],
            'hoi_phuong_thuc_xet_tuyen': ['xét tuyển', 'phương thức', 'thi', 'admission', 'entrance', 'tuyển sinh'],
            'hoi_hoc_phi': ['học phí', 'chi phí', 'tuition', 'fee', 'cost', 'tiền học', 'lệ phí'],
            'hoi_lien_he': ['liên hệ', 'contact', 'phone', 'email', 'address', 'địa chỉ', 'hotline', 'tư vấn'],
            
            # Extended admission intents
            'hoi_diem_chuan': ['điểm chuẩn', 'điểm xét tuyển', 'điểm thi', 'điểm số', 'cut-off', 'benchmark'],
            'hoi_ho_so_xet_tuyen': ['hồ sơ', 'thủ tục', 'giấy tờ', 'đăng ký', 'nộp hồ sơ', 'documents', 'application'],
            'hoi_lich_tuyen_sinh': ['lịch', 'thời gian', 'deadline', 'hạn chót', 'schedule', 'calendar', 'ngày'],
            'hoi_hoc_bong': ['học bổng', 'hỗ trợ', 'scholarship', 'tài chính', 'miễn giảm', 'trợ cấp'],
            'hoi_co_so_vat_chat': ['cơ sở vật chất', 'ký túc xá', 'dormitory', 'facilities', 'infrastructure', 'ktx'],
            'hoi_sinh_vien_quoc_te': ['quốc tế', 'international', 'nước ngoài', 'foreign', 'exchange'],
            'hoi_chuong_trinh_lien_ket': ['liên kết', 'partnership', 'collaboration', 'joint program', 'hợp tác'],
            'hoi_thuc_tap_viec_lam': ['thực tập', 'việc làm', 'internship', 'job', 'career', 'employment', 'tốt nghiệp'],
            'hoi_hoat_dong_sinh_vien': ['hoạt động', 'sinh viên', 'clb', 'club', 'activities', 'extracurricular'],
            'hoi_dao_tao_sau_dai_hoc': ['sau đại học', 'thạc sĩ', 'tiến sĩ', 'master', 'phd', 'graduate', 'postgraduate'],
            'hoi_thong_tin_chung': ['thông tin', 'general', 'about', 'overview', 'giới thiệu', 'tổng quan']
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in text for keyword in keywords):
                return intent
                
        return 'hoi_thong_tin_chung'  # Default
    
    async def crawl_and_extract_single_url(self, url: str, level: int) -> Dict:
        """Crawl single URL and extract to JSON"""
        print(f"🕷️  Level {level}: Crawling {url}")
        
        # Browser config
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        # LLM extraction strategy
        instruction = f"""
        Phân tích nội dung tuyển sinh Đại học Cần Thơ và trích xuất:
        
        1. Tạo 3-7 cặp câu hỏi-trả lời tiếng Việt về tuyển sinh
        2. Tìm tất cả URLs liên quan đến tuyển sinh CTU
        
        Yêu cầu:
        - Câu hỏi và trả lời phải bằng tiếng Việt
        - Thông tin chính xác và chi tiết
        - URLs phải liên quan đến tuyển sinh CTU
        
        Trả về JSON hợp lệ.
        """
        
        schema = {
            "type": "object",
            "properties": {
                "qa_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                            "category": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 3}
                        },
                        "required": ["question", "answer", "category", "priority"]
                    }
                },
                "urls": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["qa_pairs", "urls"]
        }
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider="openai/gpt-4o-mini",
                api_token=self.api_key
            ),
            schema=schema,
            extraction_type="schema",
            instruction=instruction,
            chunk_token_threshold=1200,
            overlap_rate=0.1
        )
        
        run_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if not result.success:
                    print(f"❌ Failed to crawl {url}: {result.error_message}")
                    return {"qa_pairs": [], "urls": [], "success": False}
                
                # Save markdown
                url_filename = url.replace("://", "_").replace("/", "_").replace("?", "_")[:100]
                md_file = f"output/auto_recursive/markdown/level_{level}_{url_filename}.md"
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(result.markdown.raw_markdown if result.markdown else "")
                
                # Process extracted content
                if result.extracted_content:
                    try:
                        extracted_data = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
                        
                        # Handle case where OpenAI returns a list instead of dict
                        if isinstance(extracted_data, list):
                            if len(extracted_data) > 0 and isinstance(extracted_data[0], dict):
                                extracted_data = extracted_data[0]  # Take first item
                            else:
                                extracted_data = {"qa_pairs": [], "urls": []}
                        
                        # Ensure required keys exist
                        if not isinstance(extracted_data, dict):
                            extracted_data = {"qa_pairs": [], "urls": []}
                        
                        qa_pairs = extracted_data.get('qa_pairs', [])
                        urls = extracted_data.get('urls', [])
                        
                        # Save JSON
                        json_file = f"output/auto_recursive/json/level_{level}_{url_filename}.json"
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Extracted {len(qa_pairs)} Q&A pairs and {len(urls)} URLs")
                        
                        return {
                            "qa_pairs": qa_pairs,
                            "urls": urls,
                            "success": True,
                            "source_url": url,
                            "level": level,
                            "crawl_time": datetime.now().isoformat()
                        }
                        
                    except Exception as e:
                        print(f"❌ Error parsing extracted content from {url}: {e}")
                        return {"qa_pairs": [], "urls": [], "success": False}
                else:
                    print(f"⚠️  No extracted content from {url}")
                    return {"qa_pairs": [], "urls": [], "success": False}
                    
        except Exception as e:
            print(f"❌ Error crawling {url}: {e}")
            return {"qa_pairs": [], "urls": [], "success": False}
    
    def organize_qa_by_intent(self, qa_pairs: List[Dict], source_url: str, level: int):
        """Organize Q&A pairs by intent"""
        for qa in qa_pairs:
            intent = self.detect_intent(qa['question'], qa['answer'])
            
            # Add metadata
            qa_with_metadata = {
                **qa,
                'intent': intent,
                'source_url': source_url,
                'level': level,
                'id': f"qa_{len(self.all_qa_pairs) + 1:04d}",
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.intent_data[intent].append(qa_with_metadata)
            self.all_qa_pairs.append(qa_with_metadata)
    
    def save_intent_data(self):
        """Save data organized by intent"""
        for intent, qa_list in self.intent_data.items():
            if qa_list:
                intent_file = f"output/auto_recursive/by_intent/{intent}.json"
                intent_dataset = {
                    'intent': intent,
                    'count': len(qa_list),
                    'updated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'qa_pairs': qa_list
                }
                
                with open(intent_file, 'w', encoding='utf-8') as f:
                    json.dump(intent_dataset, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Saved {len(qa_list)} Q&A pairs for intent: {intent}")
    
    def save_final_dataset(self):
        """Save final comprehensive dataset"""
        total_pairs = sum(len(pairs) for pairs in self.intent_data.values())
        
        final_dataset = {
            'dataset_info': {
                'name': 'CTU Auto Recursive Crawl Dataset',
                'version': '1.0',
                'description': 'Fully automated recursive crawling of CTU admission website',
                'total_pairs': total_pairs,
                'total_intents': len([intent for intent, pairs in self.intent_data.items() if pairs]),
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'crawled_urls_count': len(self.crawled_urls),
                'max_depth_reached': self.max_depth,
                'source': 'Auto Recursive Crawler'
            },
            'intents': {intent: len(pairs) for intent, pairs in self.intent_data.items()},
            'qa_pairs': self.all_qa_pairs,
            'crawled_urls': list(self.crawled_urls)
        }
        
        final_file = 'data/auto_recursive/ctu_auto_recursive_dataset.json'
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(final_dataset, f, indent=2, ensure_ascii=False)
        
        print(f"🎉 Final dataset saved: {final_file}")
        print(f"📊 Total Q&A pairs: {total_pairs}")
        print(f"🕷️ Total URLs crawled: {len(self.crawled_urls)}")
    
    async def run_recursive_crawl(self, start_url: str):
        """🚀 Main recursive crawling workflow"""
        print("🤖 Starting Auto Recursive CTU Crawler...")
        print(f"🎯 Start URL: {start_url}")
        print(f"📏 Max depth: {self.max_depth}")
        print(f"🔢 Max URLs per level: {self.max_urls_per_level}")
        print("😴 You can rest now! The system will work automatically...\n")
        
        current_urls = [start_url]
        level = 1
        
        while level <= self.max_depth and current_urls:
            print(f"\n🔄 === LEVEL {level} === ({len(current_urls)} URLs to crawl)")
            
            next_level_urls = []
            
            # Process each URL in current level
            for i, url in enumerate(current_urls[:self.max_urls_per_level], 1):
                if not self.is_valid_ctu_url(url):
                    continue
                
                print(f"[{i}/{min(len(current_urls), self.max_urls_per_level)}] ", end="")
                
                # Crawl and extract
                result = await self.crawl_and_extract_single_url(url, level)
                
                if result['success']:
                    # Mark as crawled
                    self.crawled_urls.add(url)
                    
                    # Organize Q&A by intent
                    qa_pairs = result.get('qa_pairs', [])
                    if qa_pairs:
                        self.organize_qa_by_intent(qa_pairs, url, level)
                    
                    # Collect new URLs for next level
                    new_urls = result.get('urls', [])
                    for new_url in new_urls:
                        if self.is_valid_ctu_url(new_url):
                            next_level_urls.append(new_url)
                
                # Be polite - small delay
                await asyncio.sleep(1)
            
            # Remove duplicates for next level
            current_urls = list(set(next_level_urls))
            level += 1
            
            # Save progress after each level
            self.save_intent_data()
            
            print(f"\n📈 Level {level-1} completed!")
            print(f"   Q&A pairs collected: {len(self.all_qa_pairs)}")
            print(f"   URLs found for next level: {len(current_urls)}")
        
        # Save final results
        print(f"\n🎉 Auto Recursive Crawling COMPLETED!")
        print(f"🏁 Reached level {level-1} (max: {self.max_depth})")
        self.save_final_dataset()
        
        # Summary
        print(f"\n📊 === FINAL SUMMARY ===")
        for intent, pairs in self.intent_data.items():
            if pairs:
                print(f"   {intent}: {len(pairs)} Q&A pairs")
        
        print(f"\n💤 You can wake up now! Everything is done automatically! 🎉")

async def main():
    """Main function to run the auto recursive crawler"""
    load_dotenv(override=True)
    
    # Configuration
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return
    
    start_url = "https://tuyensinh.ctu.edu.vn/"
    max_depth = 4  # Adjust as needed
    max_urls_per_level = 8  # Adjust as needed
    
    # Create and run crawler
    crawler = AutoRecursiveCTUCrawler(
        api_key=api_key,
        max_depth=max_depth,
        max_urls_per_level=max_urls_per_level
    )
    
    await crawler.run_recursive_crawl(start_url)

if __name__ == "__main__":
    asyncio.run(main()) 