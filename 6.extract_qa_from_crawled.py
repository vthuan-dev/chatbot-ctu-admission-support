import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv

def load_crawled_content(md_file):
    """
    Load content from crawled markdown file
    """
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

async def extract_qa_from_content(content, api_key, output_file):
    """
    Extract Q&A pairs from crawled content using LLM
    """
    print(f"🔍 Extracting Q&A from content ({len(content)} characters)")
    
    # Create comprehensive prompt for CTU admission data
    instruction = """
    Bạn là chuyên gia tư vấn tuyển sinh Đại học Cần Thơ (CTU). 
    Hãy phân tích nội dung và tạo ra các cặp hỏi-đáp tiếng Việt tự nhiên mà sinh viên thường hỏi.
    
    QUAN TRỌNG:
    - Tất cả câu hỏi và câu trả lời phải bằng tiếng Việt
    - Tạo câu hỏi tự nhiên như sinh viên thật sự hỏi
    - Trả lời chi tiết, chính xác dựa trên nội dung
    - Bao gồm mã ngành, chỉ tiêu, học phí, tổ hợp xét tuyển
    - Tạo nhiều câu hỏi khác nhau cho cùng một thông tin
    
    Ví dụ câu hỏi tốt:
    - "Ngành Công nghệ thông tin có mã ngành gì?"
    - "Học phí ngành CNTT chất lượng cao bao nhiêu?"
    - "Tổ hợp xét tuyển ngành Kỹ thuật phần mềm là gì?"
    - "Chỉ tiêu tuyển sinh ngành Thú y năm 2025?"
    - "Khác biệt giữa chương trình tiên tiến và chất lượng cao?"
    
    Phân loại theo priority:
    1 = Thông tin cơ bản (mã ngành, chỉ tiêu)
    2 = Thông tin quan trọng (học phí, tổ hợp)  
    3 = Thông tin chi tiết (chuyên ngành, ghi chú)
    """
    
    # Schema for Q&A extraction
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
                        "priority": {"type": "integer", "minimum": 1, "maximum": 3},
                        "entities": {
                            "type": "object",
                            "properties": {
                                "ma_nganh": {"type": "string"},
                                "ten_nganh": {"type": "string"},
                                "chi_tieu": {"type": "integer"},
                                "hoc_phi": {"type": "string"},
                                "to_hop": {"type": "array", "items": {"type": "string"}},
                                "chuong_trinh": {"type": "string"}
                            }
                        }
                    },
                    "required": ["question", "answer", "category", "priority"]
                }
            },
            "summary": {
                "type": "object",
                "properties": {
                    "total_majors": {"type": "integer"},
                    "total_quota": {"type": "integer"},
                    "special_programs": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}}
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "extraction_date": {"type": "string"},
                    "content_length": {"type": "integer"}
                }
            }
        },
        "required": ["qa_pairs", "summary"]
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
        chunk_token_threshold=2000,
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.1, "max_tokens": 6000}
    )
    
    # Use a dummy crawler just for LLM extraction
    browser_config = BrowserConfig(headless=True, verbose=False)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Create a mock result with our content
            from crawl4ai.models import CrawlResult
            
            # Use LLM strategy directly on content
            extracted_data = await llm_strategy.extract(content, {})
            
            if extracted_data:
                # Parse extracted data
                if isinstance(extracted_data, str):
                    extracted_data = json.loads(extracted_data)
                
                # Add metadata
                extracted_data['metadata'] = {
                    'source': 'crawled_ctu_admission_data',
                    'extraction_date': datetime.now().isoformat(),
                    'content_length': len(content),
                    'success': True
                }
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Extracted {len(extracted_data.get('qa_pairs', []))} Q&A pairs")
                print(f"📄 Saved to: {output_file}")
                
                return extracted_data
            else:
                print("❌ No data extracted")
                return None
                
    except Exception as e:
        print(f"❌ Exception during extraction: {str(e)}")
        return None

async def main():
    """
    Main function to extract Q&A from crawled content
    """
    # Load environment
    load_dotenv(override=True)
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Không tìm thấy OPENAI_API_KEY!")
        return
    
    # Input and output paths
    crawled_file = "output/crawled_pages/https_tuyensinh.ctu.edu.vn_chuong-trinh-dai-tra_841-danh-muc-nganh-va-chi-tieu-tuyen-sinh-dhcq.html.md"
    output_file = "output/qa_dataset/ctu_admission_qa.json"
    
    # Create output directory
    os.makedirs("output/qa_dataset", exist_ok=True)
    
    print("🚀 Bắt đầu extract Q&A từ nội dung đã crawl...")
    print(f"📁 Input: {crawled_file}")
    print(f"📁 Output: {output_file}")
    
    # Check if input file exists
    if not Path(crawled_file).exists():
        print(f"❌ File không tồn tại: {crawled_file}")
        return
    
    # Load content
    content = load_crawled_content(crawled_file)
    print(f"📄 Loaded content: {len(content)} characters")
    
    # Extract Q&A
    result = await extract_qa_from_content(content, api_key, output_file)
    
    if result:
        print(f"\n📊 Kết quả extraction:")
        print(f"   📝 Q&A pairs: {len(result.get('qa_pairs', []))}")
        print(f"   📚 Tổng ngành: {result.get('summary', {}).get('total_majors', 'N/A')}")
        print(f"   👥 Tổng chỉ tiêu: {result.get('summary', {}).get('total_quota', 'N/A')}")
        print(f"   🎓 Chương trình đặc biệt: {', '.join(result.get('summary', {}).get('special_programs', []))}")
        
        # Show some sample Q&A
        qa_pairs = result.get('qa_pairs', [])
        if qa_pairs:
            print(f"\n📝 Mẫu Q&A (3 cặp đầu):")
            for i, qa in enumerate(qa_pairs[:3], 1):
                print(f"   {i}. Q: {qa['question']}")
                print(f"      A: {qa['answer'][:100]}...")
                print(f"      Category: {qa['category']}, Priority: {qa['priority']}")
                print()

if __name__ == "__main__":
    asyncio.run(main()) 