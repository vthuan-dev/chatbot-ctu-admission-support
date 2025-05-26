import asyncio
import json
import os
from pathlib import Path
from openai import OpenAI
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_extraction_prompt():
    """Load the extraction prompt from file"""
    prompt_file = Path("prompts/extraction_prompt.txt")
    if prompt_file.exists():
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # Simplified prompt based on successful test
        return """
Tạo 6-8 cặp Q&A từ nội dung sau cho chatbot tư vấn tuyển sinh Đại học Cần Thơ.

Trả về JSON format chính xác:
{
  "qa_pairs": [
    {
      "question": "câu hỏi tiếng Việt tự nhiên",
      "answer": "câu trả lời chi tiết tiếng Việt",
      "category": "hoi_nganh_hoc",
      "priority": 1,
      "source": "URL nguồn"
    }
  ]
}

Yêu cầu:
- Câu hỏi tự nhiên như sinh viên thường hỏi
- Trả lời chính xác dựa trên nội dung
- Ưu tiên: mã ngành, học phí, xét tuyển, chỉ tiêu, liên hệ
- Category: hoi_nganh_hoc, hoi_phuong_thuc_xet_tuyen, hoi_hoc_phi, hoi_lien_he, hoi_thong_tin_chung
"""

def extract_qa_with_openai(content, source_url, prompt):
    """Extract Q&A pairs using OpenAI API"""
    try:
        # Clean and limit content
        clean_content = content.replace("**", "").replace("##", "").replace("###", "")
        # Take first 2500 chars to avoid token limits
        limited_content = clean_content[:2500]
        
        # Prepare the full prompt
        full_prompt = f"{prompt}\n\nNội dung:\n{limited_content}\n\nURL nguồn: {source_url}"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Trả về JSON hợp lệ, không có markdown hay text khác."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        
        # DEBUG: Print the raw response
        print(f"🐛 DEBUG - Raw response length: {len(result_text)}")
        print(f"🐛 DEBUG - First 200 chars: '{result_text[:200]}...'")
        
        # Try to parse directly as JSON first
        try:
            extracted_data = json.loads(result_text)
            print(f"🐛 DEBUG - Direct JSON parsing successful")
        except json.JSONDecodeError:
            print(f"🐛 DEBUG - Direct JSON parsing failed, trying markdown extraction")
            # If direct parsing fails, try to extract from markdown
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                json_text = result_text[json_start:json_end].strip()
                print(f"🐛 DEBUG - Extracted from ```json: '{json_text[:100]}...'")
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.rfind("```")
                json_text = result_text[json_start:json_end].strip()
                print(f"🐛 DEBUG - Extracted from ```: '{json_text[:100]}...'")
            elif "{" in result_text and "}" in result_text:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                json_text = result_text[json_start:json_end]
                print(f"🐛 DEBUG - Extracted JSON object: '{json_text[:100]}...'")
            else:
                print(f"⚠️ No JSON found in response")
                return {"qa_pairs": []}, 0
            
            extracted_data = json.loads(json_text)
            print(f"🐛 DEBUG - Markdown JSON parsing successful")
        
        # Validate and fix the structure
        if not isinstance(extracted_data, dict):
            print(f"🐛 DEBUG - Not a dict: {type(extracted_data)}")
            extracted_data = {"qa_pairs": []}
        
        # Handle both "qa_pairs" and "questions_answers" keys
        qa_list = []
        if "qa_pairs" in extracted_data:
            qa_list = extracted_data["qa_pairs"]
            print(f"🐛 DEBUG - Found qa_pairs key")
        elif "questions_answers" in extracted_data:
            qa_list = extracted_data["questions_answers"]
            print(f"🐛 DEBUG - Found questions_answers key, converting to qa_pairs")
        else:
            print(f"🐛 DEBUG - No qa_pairs or questions_answers key found")
            qa_list = []
        
        print(f"🐛 DEBUG - Found {len(qa_list)} raw Q&A pairs")
        
        # Add source URL and validate each Q&A pair
        valid_qa_pairs = []
        for i, qa in enumerate(qa_list):
            print(f"🐛 DEBUG - Q&A {i+1}: {type(qa)}, keys: {qa.keys() if isinstance(qa, dict) else 'N/A'}")
            if not isinstance(qa, dict):
                print(f"🐛 DEBUG - Skipping Q&A {i+1}: not a dict")
                continue
            if "question" not in qa or "answer" not in qa:
                print(f"🐛 DEBUG - Skipping Q&A {i+1}: missing question or answer")
                continue
            
            # Add missing fields
            if "source" not in qa or not qa["source"]:
                qa["source"] = source_url
            if "category" not in qa:
                qa["category"] = "hoi_thong_tin_chung"
            if "priority" not in qa:
                qa["priority"] = 2
                
            valid_qa_pairs.append(qa)
            print(f"🐛 DEBUG - Q&A {i+1}: VALID")
        
        print(f"🐛 DEBUG - Final valid Q&A pairs: {len(valid_qa_pairs)}")
        extracted_data["qa_pairs"] = valid_qa_pairs
        
        return extracted_data, response.usage.total_tokens
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response text (first 200 chars): {result_text[:200]}...")
        return {"qa_pairs": []}, 0
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return {"qa_pairs": []}, 0

def process_markdown_file(md_file, prompt, output_dir):
    """Process a single markdown file and extract Q&A"""
    try:
        print(f"📄 Processing: {md_file.name}")
        
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract URL from markdown header
        source_url = "Unknown"
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith("**URL:**"):
                source_url = line.replace("**URL:**", "").strip()
                break
        
        # Skip if content is too short
        if len(content) < 500:
            print(f"⚠️ Skipping {md_file.name} - content too short ({len(content)} chars)")
            return None, 0
        
        # Extract Q&A using OpenAI
        print(f"🤖 Extracting Q&A from {len(content):,} characters...")
        start_time = time.time()
        
        extracted_data, tokens_used = extract_qa_with_openai(content, source_url, prompt)
        
        end_time = time.time()
        
        if extracted_data and extracted_data.get("qa_pairs"):
            # Save individual extraction result
            output_file = output_dir / f"{md_file.stem}_extracted.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            qa_count = len(extracted_data.get("qa_pairs", []))
            print(f"✅ Success: {qa_count} Q&A pairs extracted in {end_time - start_time:.1f}s")
            print(f"   💰 Tokens used: {tokens_used:,}")
            print(f"   💾 Saved to: {output_file.name}")
            
            return extracted_data, tokens_used
        else:
            print(f"❌ Failed to extract Q&A from {md_file.name} (no valid Q&A pairs)")
            return None, 0
            
    except Exception as e:
        print(f"❌ Error processing {md_file.name}: {e}")
        return None, 0

def main():
    """Main function to extract Q&A from Level 5 markdown files"""
    print("🚀 Starting Level 5 Q&A extraction from markdown files...")
    
    # Check input directory
    input_dir = Path("output/crawled_pages_level5")
    if not input_dir.exists():
        print(f"❌ Input directory {input_dir} not found!")
        return
    
    # Find all markdown files
    md_files = list(input_dir.glob("*.md"))
    # Exclude summary files
    md_files = [f for f in md_files if "summary" not in f.name.lower()]
    
    print(f"📁 Found {len(md_files)} markdown files in {input_dir}")
    
    if not md_files:
        print("❌ No markdown files found to process!")
        return
    
    # Create output directory
    output_dir = Path("output/extracted_level5")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Load extraction prompt
    prompt = load_extraction_prompt()
    print(f"📝 Loaded extraction prompt ({len(prompt)} characters)")
    
    # Process each markdown file
    all_qa_pairs = []
    total_tokens = 0
    successful_extractions = 0
    
    print(f"\n🔄 Processing {len(md_files)} files...")
    
    for i, md_file in enumerate(md_files, 1):
        print(f"\n📄 [{i}/{len(md_files)}]")
        
        extracted_data, tokens_used = process_markdown_file(md_file, prompt, output_dir)
        
        if extracted_data and "qa_pairs" in extracted_data:
            all_qa_pairs.extend(extracted_data["qa_pairs"])
            total_tokens += tokens_used
            successful_extractions += 1
        
        # Small delay to be respectful to API
        time.sleep(0.5)
    
    # Create combined extraction file
    if all_qa_pairs:
        combined_data = {
            "extraction_date": datetime.now().isoformat(),
            "source": "Level 5 crawled markdown files",
            "level": "Level 5",
            "total_files_processed": len(md_files),
            "successful_extractions": successful_extractions,
            "total_qa_pairs": len(all_qa_pairs),
            "total_tokens_used": total_tokens,
            "estimated_cost_usd": total_tokens * 0.00000015,  # GPT-4o-mini pricing
            "qa_pairs": all_qa_pairs
        }
        
        combined_file = output_dir / "level5_combined_extracted.json"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Level 5 extraction completed!")
        print(f"📊 Final Statistics:")
        print(f"   📁 Files processed: {len(md_files)}")
        print(f"   ✅ Successful extractions: {successful_extractions}")
        print(f"   ❌ Failed extractions: {len(md_files) - successful_extractions}")
        print(f"   📝 Total Q&A pairs: {len(all_qa_pairs)}")
        print(f"   🤖 Total tokens used: {total_tokens:,}")
        print(f"   💰 Estimated cost: ${total_tokens * 0.00000015:.4f}")
        print(f"   💾 Combined file: {combined_file}")
        
        # Show sample Q&A pairs
        print(f"\n📝 Sample Q&A pairs:")
        for i, qa in enumerate(all_qa_pairs[:3], 1):
            print(f"   {i}. Q: {qa['question'][:60]}...")
            print(f"      A: {qa['answer'][:80]}...")
            print(f"      Category: {qa.get('category', 'unknown')}")
        
        # Show category distribution
        categories = {}
        for qa in all_qa_pairs:
            cat = qa.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n📊 Category distribution:")
        for cat, count in sorted(categories.items()):
            print(f"   📂 {cat}: {count} Q&A pairs")
        
        print(f"\n💡 Next step: Continue with Level 6 crawling or compile final dataset!")
        
    else:
        print("❌ No Q&A pairs extracted from any files!")

if __name__ == "__main__":
    main() 