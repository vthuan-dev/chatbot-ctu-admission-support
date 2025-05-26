import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
import openai


class IntentBasedExtractor:
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.intents = {
            "nganh_hoc": {
                "folder": "data/processed/nganh_hoc",
                "description": "Thông tin về các ngành học, chương trình đào tạo",
                "keywords": ["ngành", "chuyên ngành", "đào tạo", "chương trình", "khoa", "bằng cấp"]
            },
            "xet_tuyen": {
                "folder": "data/processed/xet_tuyen", 
                "description": "Phương thức xét tuyển, điều kiện, thủ tục",
                "keywords": ["xét tuyển", "phương thức", "điều kiện", "thủ tục", "hồ sơ", "đăng ký"]
            },
            "hoc_phi": {
                "folder": "data/processed/hoc_phi",
                "description": "Học phí, chi phí, học bổng",
                "keywords": ["học phí", "chi phí", "học bổng", "miễn giảm", "tài chính"]
            },
            "lien_he": {
                "folder": "data/processed/lien_he",
                "description": "Thông tin liên hệ, địa chỉ, điện thoại",
                "keywords": ["liên hệ", "địa chỉ", "điện thoại", "email", "tư vấn"]
            },
            "thong_tin": {
                "folder": "data/processed/thong_tin",
                "description": "Thông tin chung về trường, cơ sở vật chất",
                "keywords": ["giới thiệu", "lịch sử", "cơ sở", "thông tin chung", "tầm nhìn", "sứ mệnh"]
            }
        }
    
    def create_intent_folders(self):
        """Tạo các thư mục theo intent"""
        for intent_name, intent_info in self.intents.items():
            folder_path = Path(intent_info["folder"])
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {folder_path}")
    
    def classify_content_by_intent(self, content: str) -> Dict[str, str]:
        """Phân loại nội dung theo intent dựa trên keywords"""
        intent_contents = {intent: "" for intent in self.intents.keys()}
        
        # Chia content thành các đoạn
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            if len(paragraph.strip()) < 50:  # Bỏ qua đoạn quá ngắn
                continue
                
            # Tìm intent phù hợp nhất
            best_intent = "thong_tin"  # Default intent
            max_score = 0
            
            for intent_name, intent_info in self.intents.items():
                score = 0
                for keyword in intent_info["keywords"]:
                    score += paragraph.lower().count(keyword.lower())
                
                if score > max_score:
                    max_score = score
                    best_intent = intent_name
            
            intent_contents[best_intent] += paragraph + "\n\n"
        
        return intent_contents
    
    async def extract_qa_pairs_for_intent(self, content: str, intent: str) -> List[Dict[str, Any]]:
        """Trích xuất Q&A pairs cho một intent cụ thể"""
        if not content.strip():
            return []
        
        intent_info = self.intents[intent]
        
        prompt = f"""
        Bạn là chuyên gia trích xuất dữ liệu cho chatbot tư vấn tuyển sinh Đại học Cần Thơ.
        
        Từ nội dung sau về "{intent_info['description']}", hãy tạo các cặp câu hỏi-trả lời (Q&A) bằng tiếng Việt:
        
        NỘI DUNG:
        {content[:4000]}  # Giới hạn độ dài để tránh vượt quá token limit
        
        YÊU CẦU:
        1. Tạo 5-10 cặp câu hỏi-trả lời tự nhiên
        2. Câu hỏi phải như sinh viên thật sẽ hỏi
        3. Câu trả lời phải chính xác, dựa trên nội dung đã cho
        4. Tập trung vào chủ đề: {intent_info['description']}
        
        Trả về JSON format:
        {{
            "intent": "{intent}",
            "qa_pairs": [
                {{
                    "question": "Câu hỏi ví dụ?",
                    "answer": "Câu trả lời chi tiết",
                    "category": "{intent}",
                    "confidence": 0.9
                }}
            ]
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia trích xuất dữ liệu cho chatbot tư vấn tuyển sinh. Luôn trả về JSON hợp lệ."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Làm sạch JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text)
            return result.get("qa_pairs", [])
            
        except Exception as e:
            print(f"Error extracting Q&A for intent {intent}: {e}")
            return []
    
    async def process_markdown_file(self, markdown_file: str):
        """Xử lý file markdown và tạo dữ liệu theo intent"""
        print(f"Processing: {markdown_file}")
        
        # Đọc file markdown
        try:
            with open(markdown_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return
        
        print(f"Content length: {len(content)} characters")
        
        # Tạo thư mục
        self.create_intent_folders()
        
        # Phân loại nội dung theo intent
        intent_contents = self.classify_content_by_intent(content)
        
        # Xử lý từng intent
        for intent, intent_content in intent_contents.items():
            if not intent_content.strip():
                print(f"No content found for intent: {intent}")
                continue
            
            print(f"\nProcessing intent: {intent}")
            print(f"Content length: {len(intent_content)} characters")
            
            # Trích xuất Q&A pairs
            qa_pairs = await self.extract_qa_pairs_for_intent(intent_content, intent)
            
            if qa_pairs:
                # Tạo dữ liệu JSON cho intent
                intent_data = {
                    "intent": intent,
                    "description": self.intents[intent]["description"],
                    "count": len(qa_pairs),
                    "qa_pairs": qa_pairs,
                    "source": "crawl_result.md",
                    "created_date": "2025-01-27"
                }
                
                # Lưu vào file JSON
                output_file = Path(self.intents[intent]["folder"]) / f"{intent}_qa.json"
                
                # Nếu file đã tồn tại, merge dữ liệu
                if output_file.exists():
                    try:
                        with open(output_file, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                        
                        # Merge Q&A pairs
                        existing_qa_pairs = existing_data.get("qa_pairs", [])
                        all_qa_pairs = existing_qa_pairs + qa_pairs
                        
                        intent_data["qa_pairs"] = all_qa_pairs
                        intent_data["count"] = len(all_qa_pairs)
                        
                        print(f"Merged with existing data. Total Q&A pairs: {len(all_qa_pairs)}")
                    except Exception as e:
                        print(f"Error reading existing file: {e}")
                
                # Lưu file
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(intent_data, f, indent=2, ensure_ascii=False)
                
                print(f"Saved {len(qa_pairs)} Q&A pairs to: {output_file}")
            else:
                print(f"No Q&A pairs extracted for intent: {intent}")
    
    async def create_combined_dataset(self):
        """Tạo dataset tổng hợp từ tất cả các intent"""
        combined_data = {
            "dataset_info": {
                "name": "CTU Admission QA Dataset",
                "version": "1.0",
                "description": "Dataset câu hỏi-trả lời tư vấn tuyển sinh Đại học Cần Thơ",
                "created_date": "2025-01-27",
                "source": "Extracted from crawl_result.md"
            },
            "intents": {},
            "qa_pairs": []
        }
        
        total_qa_pairs = 0
        
        # Đọc dữ liệu từ tất cả các intent
        for intent, intent_info in self.intents.items():
            intent_file = Path(intent_info["folder"]) / f"{intent}_qa.json"
            
            if intent_file.exists():
                try:
                    with open(intent_file, "r", encoding="utf-8") as f:
                        intent_data = json.load(f)
                    
                    qa_pairs = intent_data.get("qa_pairs", [])
                    combined_data["intents"][intent] = len(qa_pairs)
                    combined_data["qa_pairs"].extend(qa_pairs)
                    total_qa_pairs += len(qa_pairs)
                    
                    print(f"Added {len(qa_pairs)} Q&A pairs from {intent}")
                except Exception as e:
                    print(f"Error reading {intent_file}: {e}")
        
        combined_data["dataset_info"]["total_pairs"] = total_qa_pairs
        
        # Lưu dataset tổng hợp
        output_file = Path("data/final/ctu_combined_dataset.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Combined dataset saved to: {output_file}")
        print(f"Total Q&A pairs: {total_qa_pairs}")
        print(f"Intents: {list(combined_data['intents'].keys())}")


async def main():
    """Main function"""
    load_dotenv(override=True)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return
    
    markdown_file = "output/crawl_result.md"
    
    if not os.path.exists(markdown_file):
        print(f"Error: {markdown_file} not found.")
        return
    
    # Tạo extractor
    extractor = IntentBasedExtractor(api_key)
    
    print("🚀 Starting intent-based extraction...")
    
    # Xử lý file markdown
    await extractor.process_markdown_file(markdown_file)
    
    # Tạo dataset tổng hợp
    await extractor.create_combined_dataset()
    
    print("\n🎉 Extraction completed!")


if __name__ == "__main__":
    asyncio.run(main()) 