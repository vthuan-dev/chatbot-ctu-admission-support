import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def debug_extraction():
    """Debug extraction on one specific file"""
    
    # Pick one file to debug
    test_file = Path("output/crawled_pages_level5/https_tuyensinh.ctu.edu.vn_dai-hoc-chinh-quy_thong-tin-tuyen-sinh.html.md")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    # Read the file
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Testing file: {test_file.name}")
    print(f"📊 File size: {len(content):,} characters")
    
    # Show first 500 chars of content
    print(f"\n📝 First 500 characters:")
    print(f"'{content[:500]}...'")
    
    # Clean and limit content like in the main script
    clean_content = content.replace("**", "").replace("##", "").replace("###", "")
    limited_content = clean_content[:2500]
    
    print(f"\n🧹 After cleaning and limiting: {len(limited_content):,} characters")
    print(f"📝 First 300 characters of limited content:")
    print(f"'{limited_content[:300]}...'")
    
    # Simple prompt
    prompt = """
Tạo 3 cặp Q&A từ nội dung sau cho chatbot tư vấn tuyển sinh Đại học Cần Thơ.

Trả về JSON format chính xác:
{
  "qa_pairs": [
    {
      "question": "câu hỏi tiếng Việt tự nhiên",
      "answer": "câu trả lời chi tiết tiếng Việt",
      "category": "hoi_thong_tin_chung",
      "priority": 1,
      "source": "test"
    }
  ]
}
"""
    
    full_prompt = f"{prompt}\n\nNội dung:\n{limited_content}"
    
    try:
        print(f"\n🤖 Calling OpenAI API...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Trả về JSON hợp lệ, không có markdown hay text khác."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        print(f"📝 Raw OpenAI response:")
        print(f"'{result}'")
        print(f"\n📊 Response length: {len(result)} characters")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(result)
            print(f"✅ JSON parsing successful!")
            print(f"📄 Parsed structure: {type(parsed)}")
            
            if isinstance(parsed, dict) and "qa_pairs" in parsed:
                qa_pairs = parsed["qa_pairs"]
                print(f"📝 Found {len(qa_pairs)} Q&A pairs")
                
                for i, qa in enumerate(qa_pairs, 1):
                    print(f"   {i}. Q: {qa.get('question', 'N/A')}")
                    print(f"      A: {qa.get('answer', 'N/A')[:60]}...")
                    print(f"      Valid: {isinstance(qa, dict) and 'question' in qa and 'answer' in qa}")
            else:
                print(f"❌ No qa_pairs found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            
            # Try to extract from markdown
            if "```json" in result:
                json_start = result.find("```json") + 7
                json_end = result.find("```", json_start)
                json_text = result[json_start:json_end].strip()
                print(f"🔧 Extracted from markdown: '{json_text}'")
                
                try:
                    parsed = json.loads(json_text)
                    print(f"✅ Markdown JSON parsing successful!")
                    print(f"📄 Parsed data: {parsed}")
                except json.JSONDecodeError as e2:
                    print(f"❌ Markdown JSON parsing also failed: {e2}")
        
    except Exception as e:
        print(f"❌ API error: {e}")

if __name__ == "__main__":
    print("🐛 Debugging Level 5 extraction...")
    debug_extraction() 