import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv

# Cấu trúc crawl theo intent và sub-topics
CRAWL_STRUCTURE = {
    "hoi_nganh_hoc": {
        "description": "Câu hỏi về ngành học",
        "targets": [
            {
                "url": "https://tuyensinh.ctu.edu.vn/danh-muc-nganh-va-chi-tieu-tuyen-sinh",
                "filename": "001_danh_sach_nganh",
                "description": "Danh sách ngành và chỉ tiêu",
                "prompt": "Extract all major names, codes, quotas. Create Q&A pairs about available majors in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/nganh-dao-tao-chat-luong-cao",
                "filename": "002_nganh_chat_luong_cao", 
                "description": "Ngành đào tạo chất lượng cao",
                "prompt": "Extract information about high-quality training programs. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/nganh-dao-tao-tien-tien",
                "filename": "003_nganh_tien_tien",
                "description": "Ngành đào tạo tiên tiến", 
                "prompt": "Extract information about advanced training programs. Create Q&A pairs in Vietnamese."
            }
        ]
    },
    "hoi_phuong_thuc_xet_tuyen": {
        "description": "Câu hỏi về phương thức xét tuyển",
        "targets": [
            {
                "url": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen",
                "filename": "001_tong_quan_phuong_thuc",
                "description": "Tổng quan phương thức xét tuyển",
                "prompt": "Extract overview of all admission methods. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/xet-tuyen-hoc-ba",
                "filename": "002_xet_tuyen_hoc_ba",
                "description": "Xét tuyển học bạ",
                "prompt": "Extract information about transcript-based admission. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/xet-tuyen-ket-qua-thi-thpt",
                "filename": "003_xet_tuyen_thi_thpt",
                "description": "Xét tuyển kết quả thi THPT",
                "prompt": "Extract information about high school exam-based admission. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/xet-tuyen-vsat",
                "filename": "004_xet_tuyen_vsat",
                "description": "Xét tuyển V-SAT",
                "prompt": "Extract information about V-SAT admission method. Create Q&A pairs in Vietnamese."
            }
        ]
    },
    "hoi_hoc_phi": {
        "description": "Câu hỏi về học phí",
        "targets": [
            {
                "url": "https://tuyensinh.ctu.edu.vn/hoc-phi",
                "filename": "001_hoc_phi_dai_tra",
                "description": "Học phí đại trà",
                "prompt": "Extract tuition fees for regular programs. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/hoc-phi-chat-luong-cao",
                "filename": "002_hoc_phi_chat_luong_cao",
                "description": "Học phí chất lượng cao",
                "prompt": "Extract tuition fees for high-quality programs. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/hoc-bong-ho-tro",
                "filename": "003_hoc_bong_ho_tro",
                "description": "Học bổng và hỗ trợ",
                "prompt": "Extract scholarship and financial aid information. Create Q&A pairs in Vietnamese."
            }
        ]
    },
    "hoi_lien_he": {
        "description": "Câu hỏi về liên hệ",
        "targets": [
            {
                "url": "https://tuyensinh.ctu.edu.vn/lien-he",
                "filename": "001_thong_tin_lien_he",
                "description": "Thông tin liên hệ",
                "prompt": "Extract contact information, phone, email, address. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/dia-chi-tu-van",
                "filename": "002_dia_chi_tu_van",
                "description": "Địa chỉ tư vấn",
                "prompt": "Extract counseling locations and office hours. Create Q&A pairs in Vietnamese."
            }
        ]
    },
    "hoi_thong_tin_chung": {
        "description": "Câu hỏi thông tin chung",
        "targets": [
            {
                "url": "https://tuyensinh.ctu.edu.vn/",
                "filename": "001_trang_chu_tuyen_sinh",
                "description": "Trang chủ tuyển sinh",
                "prompt": "Extract general admission information and announcements. Create Q&A pairs in Vietnamese."
            },
            {
                "url": "https://tuyensinh.ctu.edu.vn/thong-bao-tuyen-sinh",
                "filename": "002_thong_bao_tuyen_sinh",
                "description": "Thông báo tuyển sinh",
                "prompt": "Extract admission announcements and important dates. Create Q&A pairs in Vietnamese."
            }
        ]
    }
}

async def crawl_single_target(crawler, intent, target, api_key, base_output_dir):
    """
    Crawl một target cụ thể trong intent
    """
    # Tạo thư mục cho intent
    intent_dir = Path(base_output_dir) / intent
    intent_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"\n🔍 Intent: {intent}")
    print(f"📄 File: {target['filename']}")
    print(f"📍 URL: {target['url']}")
    
    # Tạo prompt cụ thể
    instruction = f"""
    You are extracting data for intent: {intent}
    Topic: {target['description']}
    
    {target['prompt']}
    
    Requirements:
    - Create natural Vietnamese Q&A pairs
    - Focus on this specific topic within the intent
    - Extract detailed and accurate information
    - Use proper Vietnamese language
    - Include relevant entities and structured data
    
    Return structured data with Q&A pairs and relevant information.
    """
    
    # Schema cho từng target
    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "topic": {"type": "string"},
            "qa_pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "priority": {"type": "integer", "minimum": 1, "maximum": 3},
                        "entities": {"type": "object"}
                    },
                    "required": ["question", "answer", "priority"]
                }
            },
            "structured_data": {
                "type": "object",
                "description": "Structured information extracted from the page"
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "intent": {"type": "string"},
                    "topic": {"type": "string"},
                    "crawl_date": {"type": "string"}
                }
            }
        },
        "required": ["intent", "topic", "qa_pairs"]
    }
    
    # Configure LLM strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key
        ),
        schema=schema,
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1200,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 4000}
    )
    
    # Configure crawler run
    run_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )
    
    try:
        # Run crawler
        result = await crawler.arun(url=target['url'], config=run_config)
        
        if result.success and result.extracted_content:
            # Parse extracted data
            extracted_data = json.loads(result.extracted_content) if isinstance(result.extracted_content, str) else result.extracted_content
            
            # Add metadata
            if isinstance(extracted_data, dict):
                extracted_data['metadata'] = {
                    'url': target['url'],
                    'intent': intent,
                    'topic': target['description'],
                    'filename': target['filename'],
                    'crawl_date': datetime.now().isoformat(),
                    'success': True
                }
            
            # Save JSON file
            json_file = intent_dir / f"{target['filename']}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            # Save markdown file
            md_file = intent_dir / f"{target['filename']}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(result.markdown.raw_markdown if hasattr(result, 'markdown') and result.markdown else "")
            
            print(f"✅ Thành công: {json_file}")
            return extracted_data
            
        else:
            print(f"❌ Lỗi crawl: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

async def main():
    """
    Main function để crawl theo cấu trúc intent
    """
    # Load environment
    load_dotenv(override=True)
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Không tìm thấy OPENAI_API_KEY!")
        return
    
    # Setup output directory
    base_output_dir = "output/intents"
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Browser config
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    print("🚀 Bắt đầu crawl theo cấu trúc intent...")
    print(f"📁 Base output directory: {base_output_dir}")
    
    results = {}
    total_targets = sum(len(intent_data['targets']) for intent_data in CRAWL_STRUCTURE.values())
    current_target = 0
    
    # Crawl each intent and its targets
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for intent, intent_data in CRAWL_STRUCTURE.items():
            print(f"\n📂 Intent: {intent} - {intent_data['description']}")
            results[intent] = {}
            
            for target in intent_data['targets']:
                current_target += 1
                print(f"\n[{current_target}/{total_targets}]", end=" ")
                
                result = await crawl_single_target(crawler, intent, target, api_key, base_output_dir)
                results[intent][target['filename']] = result
                
                # Delay between requests
                await asyncio.sleep(2)
    
    # Create overall summary
    summary = {
        "crawl_summary": {
            "total_intents": len(CRAWL_STRUCTURE),
            "total_targets": total_targets,
            "successful_crawls": sum(
                len([r for r in intent_results.values() if r is not None])
                for intent_results in results.values()
            ),
            "failed_crawls": sum(
                len([r for r in intent_results.values() if r is None])
                for intent_results in results.values()
            ),
            "crawl_date": datetime.now().isoformat(),
            "structure": {intent: list(intent_data.keys()) for intent, intent_data in results.items()}
        },
        "results": results
    }
    
    # Save summary
    summary_file = Path(base_output_dir) / "crawl_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Tổng kết:")
    print(f"   📂 Intents: {summary['crawl_summary']['total_intents']}")
    print(f"   📄 Targets: {summary['crawl_summary']['total_targets']}")
    print(f"   ✅ Thành công: {summary['crawl_summary']['successful_crawls']}")
    print(f"   ❌ Thất bại: {summary['crawl_summary']['failed_crawls']}")
    print(f"   📄 Summary: {summary_file}")
    
    # Show folder structure
    print(f"\n📁 Cấu trúc thư mục:")
    for intent in CRAWL_STRUCTURE.keys():
        intent_dir = Path(base_output_dir) / intent
        if intent_dir.exists():
            files = list(intent_dir.glob("*.json"))
            print(f"   📂 {intent}/ ({len(files)} files)")
            for file in sorted(files):
                print(f"      📄 {file.name}")

if __name__ == "__main__":
    asyncio.run(main()) 