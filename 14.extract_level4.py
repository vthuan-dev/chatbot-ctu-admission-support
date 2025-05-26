import asyncio
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv(override=True)

# Initialize OpenAI client at module level
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_qa_from_markdown(markdown_content, filename):
    """
    Extract Q&A pairs from markdown content using OpenAI API
    """
    # Use the global client instead of creating a new one
    
    prompt = f"""
    Bạn là chuyên gia tư vấn tuyển sinh Đại học Cần Thơ (CTU). 
    Hãy phân tích nội dung markdown và tạo ra các cặp hỏi-đáp tiếng Việt tự nhiên.
    
    QUAN TRỌNG:
    - Tất cả câu hỏi và câu trả lời phải bằng tiếng Việt
    - Tạo câu hỏi tự nhiên như sinh viên thật sự hỏi
    - Trả lời chi tiết, chính xác dựa trên nội dung
    - Bao gồm mã ngành, chỉ tiêu, học phí, tổ hợp xét tuyển
    - Tạo 5-8 Q&A pairs từ nội dung
    
    Trả về JSON format:
    {{
        "qa_pairs": [
            {{
                "question": "Câu hỏi tiếng Việt",
                "answer": "Câu trả lời chi tiết tiếng Việt",
                "category": "hoi_nganh_hoc|hoi_phuong_thuc_xet_tuyen|hoi_hoc_phi|hoi_lien_he|hoi_thong_tin_chung",
                "priority": 1-3,
                "source": "{filename}"
            }}
        ]
    }}
    
    Nội dung markdown:
    {markdown_content[:4000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia tư vấn tuyển sinh CTU. Trả về JSON hợp lệ."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        # Clean JSON response
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        
        return json.loads(result.strip())
        
    except Exception as e:
        print(f"❌ Error extracting from {filename}: {e}")
        return {"qa_pairs": []}

def main():
    """
    Extract Q&A pairs from all markdown files in Level 4
    """
    # Remove duplicate load_dotenv since it's already at module level
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ No OpenAI API key found!")
        return
    
    markdown_dir = Path("output/crawled_pages_level4")
    output_dir = Path("output/extracted_level4")
    output_dir.mkdir(exist_ok=True)
    
    if not markdown_dir.exists():
        print(f"❌ Directory {markdown_dir} not found!")
        return
    
    markdown_files = list(markdown_dir.glob("*.md"))
    # Exclude summary files
    markdown_files = [f for f in markdown_files if "summary" not in f.name.lower()]
    
    print(f"🔍 Found {len(markdown_files)} markdown files to extract from Level 4")
    
    all_qa_pairs = []
    total_cost = 0
    
    for i, md_file in enumerate(markdown_files, 1):
        print(f"\n📄 [{i}/{len(markdown_files)}] Processing: {md_file.name}")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content.strip()) < 100:
                print(f"⚠️ Skipping {md_file.name} - too short")
                continue
            
            # Extract Q&A pairs
            result = extract_qa_from_markdown(content, md_file.name)
            qa_pairs = result.get('qa_pairs', [])
            
            if qa_pairs:
                print(f"✅ Extracted {len(qa_pairs)} Q&A pairs")
                all_qa_pairs.extend(qa_pairs)
                
                # Save individual file
                output_file = output_dir / f"{md_file.stem}_extracted.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                # Estimate cost (rough)
                tokens_used = len(content[:4000]) // 4 + 500  # Rough estimate
                cost = tokens_used * 0.00000015  # GPT-4o-mini pricing
                total_cost += cost
                
            else:
                print(f"❌ No Q&A pairs extracted from {md_file.name}")
                
        except Exception as e:
            print(f"❌ Error processing {md_file.name}: {e}")
    
    # Save combined results
    combined_file = output_dir / "level4_combined_extracted.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_qa_pairs": len(all_qa_pairs),
            "source_files": len(markdown_files),
            "level": "Level 4",
            "qa_pairs": all_qa_pairs
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Level 4 Extraction completed!")
    print(f"📊 Total Q&A pairs: {len(all_qa_pairs)}")
    print(f"💰 Estimated cost: ~${total_cost:.4f}")
    print(f"📁 Results saved in: {output_dir}")
    print(f"📄 Combined file: {combined_file}")
    
    # Show sample Q&A
    print(f"\n📝 Sample Q&A pairs (first 3):")
    for i, qa in enumerate(all_qa_pairs[:3], 1):
        print(f"   {i}. Q: {qa.get('question', 'N/A')}")
        print(f"      A: {qa.get('answer', 'N/A')[:80]}...")
        print(f"      Category: {qa.get('category', 'N/A')}, Priority: {qa.get('priority', 'N/A')}")
        print()
    
    print(f"💡 Next: Run final dataset creation to combine all levels!")

if __name__ == "__main__":
    main() 