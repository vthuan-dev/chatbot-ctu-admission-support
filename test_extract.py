import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def test_extraction():
    """Test extraction with a simple prompt"""
    
    # Simple test content
    test_content = """
    Trường Đại học Cần Thơ tuyển sinh năm 2025 với 117 mã ngành.
    Học phí chương trình chất lượng cao là 37-40 triệu VND/năm.
    Liên hệ: 0292.3872728 hoặc tuyensinh@ctu.edu.vn
    """
    
    # Simple prompt
    prompt = """
Tạo 3 cặp Q&A từ nội dung sau. Trả về JSON format chính xác:

{
  "qa_pairs": [
    {
      "question": "câu hỏi",
      "answer": "câu trả lời", 
      "category": "hoi_thong_tin_chung",
      "priority": 1
    }
  ]
}

Nội dung: """ + test_content
    
    try:
        print("🤖 Testing OpenAI extraction...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Trả về JSON hợp lệ, không có markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        print(f"📝 Raw response:")
        print(f"'{result}'")
        print(f"\n📊 Response length: {len(result)} characters")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(result)
            print(f"✅ JSON parsing successful!")
            print(f"📄 Parsed data: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            
            # Try to extract JSON from markdown
            if "```json" in result:
                json_start = result.find("```json") + 7
                json_end = result.find("```", json_start)
                json_text = result[json_start:json_end].strip()
                print(f"🔧 Extracted JSON from markdown: '{json_text}'")
                
                try:
                    parsed = json.loads(json_text)
                    print(f"✅ Markdown JSON parsing successful!")
                    print(f"📄 Parsed data: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
                    return True
                except json.JSONDecodeError as e2:
                    print(f"❌ Markdown JSON parsing also failed: {e2}")
            
            return False
            
    except Exception as e:
        print(f"❌ API error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing OpenAI API extraction...")
    success = test_extraction()
    if success:
        print("\n🎉 Test successful! The API is working correctly.")
    else:
        print("\n❌ Test failed! Need to fix the prompt or parsing logic.") 