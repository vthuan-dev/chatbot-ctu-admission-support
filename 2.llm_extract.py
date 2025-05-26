import asyncio
import json
import os
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv
from models.admission_schema import AdmissionDataSchema


def extract_urls_from_markdown(markdown_content):
    """
    Extract all URLs from markdown content with CTU admission-specific categorization.
    Returns a list of unique URLs with metadata and priority for admission-related content.
    """
    urls = []
    
    # Pattern for markdown links: [text](url)
    markdown_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
    
    # Pattern for direct URLs: http(s)://...
    direct_url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
    
    # Define CTU admission-related keywords for categorization
    admission_keywords = {
        'nganh_hoc': ['ngành', 'chuyên ngành', 'mã ngành', 'đào tạo', 'bậc đại học', 'giới thiệu ngành'],
        'phuong_thuc_xet_tuyen': ['phương thức', 'xét tuyển', 'tuyển thẳng', 'thi tốt nghiệp', 'học bạ', 'v-sat', 'vsat'],
        'chi_tieu': ['chỉ tiêu', 'ngành và chỉ tiêu', 'tuyển sinh'],
        'hoc_phi': ['học phí', 'chi phí', 'tài chính', 'học bổng'],
        'chuong_trinh': ['chương trình tiên tiến', 'chất lượng cao', 'đại trà', 'cttt', 'ctclc'],
        'thong_tin_tuyen_sinh': ['thông tin tuyển sinh', 'đại học chính quy', 'tuyển sinh'],
        'lien_he': ['liên hệ', 'tư vấn', 'facebook', 'email', 'điện thoại'],
        'de_an': ['đề án', 'quy chế', 'quyết định', 'văn bản'],
        'lich_thi': ['lịch thi', 'tổ chức thi', 'thời gian thi'],
        'ktx_csvc': ['ký túc xá', 'cơ sở vật chất', 'tân sinh viên']
    }
    
    def categorize_url(url_text, url_link):
        """Categorize URL based on text content and URL path"""
        text_lower = url_text.lower()
        url_lower = url_link.lower()
        combined_text = f"{text_lower} {url_lower}"
        
        # Check for CTU domain first
        if 'ctu.edu.vn' not in url_lower:
            return 'external', 3
            
        # Prioritize admission-related URLs
        for category, keywords in admission_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    # Higher priority for core admission information
                    if category in ['nganh_hoc', 'phuong_thuc_xet_tuyen', 'chi_tieu', 'thong_tin_tuyen_sinh']:
                        return category, 1
                    elif category in ['chuong_trinh', 'hoc_phi', 'lich_thi']:
                        return category, 2
                    else:
                        return category, 3
        
        # Default categorization for CTU URLs
        if 'tuyensinh' in url_lower:
            return 'thong_tin_tuyen_sinh', 2
        elif any(x in url_lower for x in ['ctc.ctu.edu.vn', 'gs.ctu.edu.vn']):
            return 'chuong_trinh_khac', 3
        else:
            return 'thong_tin_chung', 3
    
    # Extract markdown links
    markdown_matches = re.findall(markdown_link_pattern, markdown_content)
    for text, url in markdown_matches:
        if url.startswith(('http://', 'https://')):
            category, priority = categorize_url(text, url)
            urls.append({
                'url': url.strip(),
                'text': text.strip(),
                'type': 'markdown_link',
                'category': category,
                'priority': priority
            })
    
    # Extract direct URLs
    direct_matches = re.findall(direct_url_pattern, markdown_content)
    for url in direct_matches:
        # Skip if already found in markdown links
        if not any(existing['url'] == url.strip() for existing in urls):
            category, priority = categorize_url(url, url)
            urls.append({
                'url': url.strip(),
                'text': url.strip(),
                'type': 'direct_url',
                'category': category,
                'priority': priority
            })
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen_urls = set()
    for url_info in urls:
        if url_info['url'] not in seen_urls:
            unique_urls.append(url_info)
            seen_urls.add(url_info['url'])
    
    # Sort by priority (1 = highest, 3 = lowest) and then by category
    unique_urls.sort(key=lambda x: (x['priority'], x['category']))
    
    return unique_urls


async def main():
    """
    Extract structured JSON data from existing markdown file using LLM.
    
    Args:
        markdown_file: Path to the markdown file to process
        schema: JSON schema for extraction
        output_dir: Directory to save results (optional)
        prompt: Custom prompt for LLM extraction (optional)
        api_key: OpenAI API key (uses environment variable if not provided)
    """
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
        return
    
    # Load instruction from CTU admission specific prompt file
    try:
        with open("prompts/ctu_admission_extract_prompt.txt", "r", encoding="utf-8") as f:
            instruction = f.read()
        print("✅ Loaded CTU admission extraction prompt")
    except FileNotFoundError:
        print("⚠️ ctu_admission_extract_prompt.txt not found. Using fallback prompt.")
        instruction = """
        Bạn là chuyên gia tư vấn tuyển sinh Đại học Cần Thơ (CTU). 
        Tạo các câu hỏi-trả lời cụ thể về ngành học, mã ngành, học phí, thời gian đào tạo.
        
        YÊU CẦU:
        - Câu trả lời phải có số liệu cụ thể
        - Không được nói "tham khảo thêm" hoặc "liên hệ"
        - Tập trung vào 117 ngành học CTU 2025
        
        Trả về JSON format với qa_pairs chứa thông tin chi tiết.
        """
    
    # Target markdown file
    markdown_file = "output/crawl_result.md"
    
    print(f"🎯 Target file: {markdown_file}")
    
    # Check if file exists
    if not os.path.exists(markdown_file):
        print(f"❌ File not found: {markdown_file}")
        return
    
    # Read markdown content
    try:
        with open(markdown_file, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        print(f"📄 Loaded markdown file: {len(markdown_content)} characters")
        
        # Extract URLs from markdown content
        extracted_urls = extract_urls_from_markdown(markdown_content)
        print(f"🔗 Found {len(extracted_urls)} URLs in markdown content")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",  # Changed to OpenAI GPT-4o-mini for cost efficiency
            api_token=api_key
        ),
        schema=AdmissionDataSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1500,  # Increased for better processing
        overlap_rate=0.1,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 6000}  # Increased for more Q&A pairs
    )
        
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Process the markdown content using direct OpenAI API
    print("🚀 Starting extraction from markdown file...")
    
    try:
        # Direct OpenAI approach
        import openai
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # First, get summary of URLs for context
        url_summary = []
        high_priority_urls = [url for url in extracted_urls if url['priority'] <= 2]
        for url_info in high_priority_urls[:10]:  # Top 10 most relevant URLs
            url_summary.append(f"- {url_info['text']} ({url_info['category']}) - {url_info['url']}")
        
        urls_context = "\n".join(url_summary) if url_summary else "Không có URL ưu tiên cao"

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia trích xuất dữ liệu cho chatbot tư vấn tuyển sinh CTU. Tạo các câu hỏi-trả lời CỤ THỂ dựa trên dữ liệu thực tế. LUÔN trả về JSON CHÍNH XÁC."},
                {"role": "user", "content": f"""
{instruction}

THÔNG TIN URL TUYỂN SINH CTU ĐÃ TRÍCH XUẤT:
{urls_context}

QUAN TRỌNG - Trả về JSON CHÍNH XÁC theo format này:
{{
  "intent": "tuyen_sinh_ctu",
  "description": "Câu hỏi-trả lời về tuyển sinh CTU 2025 với thông tin cụ thể từ website",
  "count": 25,
  "qa_pairs": [
    {{
      "id": "qa_001",
      "question": "Câu hỏi cụ thể về tuyển sinh CTU",
      "answer": "Câu trả lời chi tiết với thông tin cụ thể từ website",
      "intent": "nganh_hoc",
      "category": "nganh_hoc",
      "confidence": 0.9,
      "source_url": "tuyensinh.ctu.edu.vn",
      "source_type": "official_website",
      "created_date": "2025-01-27"
    }}
  ],
  "extracted_urls": [],
  "source": "ctu_admission_website_2025",
  "created_date": "2025-01-27",
  "last_updated": "2025-01-27"
}}

YÊU CẦU TẠO CÂUHỎI:
1. Phân tích danh sách URL để tạo câu hỏi về các chủ đề chính
2. Tạo câu hỏi về phương thức xét tuyển (có 6 phương thức)
3. Tạo câu hỏi về ngành học và mã ngành cụ thể
4. Tạo câu hỏi về chương trình tiên tiến và chất lượng cao
5. Tạo câu hỏi về thông tin liên hệ và tư vấn

NỘI DUNG WEBSITE TUYỂN SINH CTU:
{markdown_content[:12000]}
"""}
            ],
            temperature=0.0,
            max_tokens=6000
        )
        
        extracted_content = response.choices[0].message.content
        
        print("✅ Extraction successful!")
        
        # Create a mock result object for compatibility
        class MockResult:
            def __init__(self, extracted_content, markdown_content):
                self.success = True
                self.extracted_content = extracted_content
                self.markdown = type('obj', (object,), {'raw_markdown': markdown_content})()
        
        result = MockResult(extracted_content, markdown_content)
        
        # Display results
        print(f"Processing successful: {result.success}")
        
        # Process extracted content
        if hasattr(result, 'extracted_content') and result.extracted_content:
            print("\nExtracted JSON data:")
            try:
                # Clean up markdown formatting if present
                content = result.extracted_content.strip()
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                if content.endswith('```'):
                    content = content[:-3]  # Remove ```
                content = content.strip()
                
                extracted_data = json.loads(content)
                
                # Add extracted URLs if not present in LLM response
                if 'extracted_urls' not in extracted_data or not extracted_data['extracted_urls']:
                    extracted_data['extracted_urls'] = extracted_urls
                    print(f"🔗 Added {len(extracted_urls)} URLs to extracted data")
                
                # Display URL analysis summary
                print("\n📊 PHÂN TÍCH URL TUYỂN SINH CTU:")
                url_stats = {}
                for url in extracted_urls:
                    category = url['category']
                    priority = url['priority']
                    if category not in url_stats:
                        url_stats[category] = {'total': 0, 'high_priority': 0}
                    url_stats[category]['total'] += 1
                    if priority <= 2:
                        url_stats[category]['high_priority'] += 1
                
                for category, stats in sorted(url_stats.items()):
                    print(f"  📂 {category}: {stats['total']} URLs (ưu tiên cao: {stats['high_priority']})")
                
                print(f"\n🔗 TOP 10 URL TUYỂN SINH CTU QUAN TRỌNG NHẤT:")
                high_priority_urls = [url for url in extracted_urls if url['priority'] <= 2]
                for i, url in enumerate(high_priority_urls[:10], 1):
                    print(f"  {i:2d}. [{url['category']}] {url['text']}")
                    print(f"      🌐 {url['url']}")
                
                print(f"\n✅ TỔNG KẾT:")
                print(f"  📄 Tổng số URL: {len(extracted_urls)}")
                print(f"  🎯 URL ưu tiên cao: {len(high_priority_urls)}")
                print(f"  🤖 Q&A pairs: {extracted_data.get('count', 0)}")
                
                print("\n📋 JSON DATA:")
                print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
                
                # Save the extracted JSON if output directory is specified
                if output_dir:
                    output_path = Path(output_dir)
                    output_path.mkdir(exist_ok=True, parents=True)
                    
                    # Determine intent from extracted data
                    intent = extracted_data.get('intent', 'thong_tin_chung')
                    
                    # Create intent-based directory structure
                    intent_dir = output_path / "processed" / intent
                    intent_dir.mkdir(exist_ok=True, parents=True)
                    
                    # Save JSON with intent-based filename
                    json_file = intent_dir / f"{intent}_qa.json"
                    
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                    
                    # Save URLs to separate file for reference
                    urls_file = intent_dir / f"{intent}_urls.json"
                    urls_data = {
                        "total_urls": len(extracted_urls),
                        "high_priority_urls": len(high_priority_urls),
                        "url_categories": url_stats,
                        "urls": extracted_urls,
                        "generated_date": "2025-01-27"
                    }
                    
                    with open(urls_file, "w", encoding="utf-8") as f:
                        json.dump(urls_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"\n✅ SAVED FILES:")
                    print(f"  📄 Q&A JSON: {json_file}")
                    print(f"  🔗 URLs JSON: {urls_file}")
                    print(f"  📊 Generated {extracted_data.get('count', 0)} Q&A pairs")
                    print(f"  🎯 Intent: {intent}")
                    print(f"  📝 Description: {extracted_data.get('description', 'N/A')}")
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print("Raw extracted content:")
                print(result.extracted_content)
                
                # Save raw content for debugging
                raw_file = Path(output_dir) / f"{Path(markdown_file).stem}_raw.txt"
                with open(raw_file, "w", encoding="utf-8") as f:
                    f.write(result.extracted_content)
                print(f"Raw content saved to: {raw_file}")
                
            except Exception as e:
                print(f"Error processing extracted content: {e}")
        else:
            print("\nNo structured data was extracted or extraction failed.")
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return

if __name__ == "__main__":
    load_dotenv(override=True)
    asyncio.run(main()) 