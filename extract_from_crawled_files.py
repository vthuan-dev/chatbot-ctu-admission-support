import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai


class CrawledFilesExtractor:
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.intents = {
            "nganh_hoc": {
                "folder": "data/processed/nganh_hoc",
                "description": "Thông tin về các ngành học, chương trình đào tạo",
                "keywords": ["ngành", "chuyên ngành", "đào tạo", "chương trình", "khoa", "bằng cấp", "tuyển sinh", "mã ngành", "chỉ tiêu"]
            },
            "xet_tuyen": {
                "folder": "data/processed/xet_tuyen", 
                "description": "Phương thức xét tuyển, điều kiện, thủ tục",
                "keywords": ["xét tuyển", "phương thức", "điều kiện", "thủ tục", "hồ sơ", "đăng ký", "tổ hợp", "điểm chuẩn", "tuyển thẳng"]
            },
            "hoc_phi": {
                "folder": "data/processed/hoc_phi",
                "description": "Học phí, chi phí, học bổng",
                "keywords": ["học phí", "chi phí", "học bổng", "miễn giảm", "tài chính", "kinh phí", "phí", "tiền", "học bổng"]
            },
            "lien_he": {
                "folder": "data/processed/lien_he",
                "description": "Thông tin liên hệ, địa chỉ, điện thoại",
                "keywords": ["liên hệ", "địa chỉ", "điện thoại", "email", "tư vấn", "hotline", "contact", "phone", "address"]
            },
            "sinh_vien": {
                "folder": "data/processed/sinh_vien",
                "description": "Hoạt động sinh viên, câu lạc bộ, đoàn thể",
                "keywords": ["sinh viên", "hoạt động", "câu lạc bộ", "đoàn", "hội", "sự kiện", "festival", "thi đấu", "thể thao", "văn nghệ"]
            },
            "nghien_cuu": {
                "folder": "data/processed/nghien_cuu",
                "description": "Nghiên cứu khoa học, dự án, công bố",
                "keywords": ["nghiên cứu", "khoa học", "dự án", "công bố", "bài báo", "hội thảo", "seminar", "research", "publication"]
            },
            "sau_dai_hoc": {
                "folder": "data/processed/sau_dai_hoc",
                "description": "Chương trình sau đại học, thạc sĩ, tiến sĩ",
                "keywords": ["sau đại học", "thạc sĩ", "tiến sĩ", "cao học", "graduate", "master", "phd", "doctorate", "postgraduate"]
            },
            "quoc_te": {
                "folder": "data/processed/quoc_te",
                "description": "Hợp tác quốc tế, trao đổi sinh viên, chương trình liên kết",
                "keywords": ["quốc tế", "hợp tác", "trao đổi", "liên kết", "international", "exchange", "partnership", "abroad", "global"]
            },
            "dich_vu": {
                "folder": "data/processed/dich_vu",
                "description": "Dịch vụ sinh viên, thư viện, ký túc xá, y tế",
                "keywords": ["dịch vụ", "thư viện", "ký túc xá", "y tế", "canteen", "library", "dormitory", "medical", "service", "facility"]
            },
            "cuu_sinh_vien": {
                "folder": "data/processed/cuu_sinh_vien",
                "description": "Cựu sinh viên, mạng lưới alumni, việc làm",
                "keywords": ["cựu sinh viên", "alumni", "việc làm", "career", "job", "employment", "mạng lưới", "network", "graduate"]
            },
            "xuat_ban": {
                "folder": "data/processed/xuat_ban",
                "description": "Xuất bản, tạp chí, sách, tài liệu",
                "keywords": ["xuất bản", "tạp chí", "sách", "tài liệu", "publication", "journal", "book", "document", "material"]
            },
            "thong_tin": {
                "folder": "data/processed/thong_tin",
                "description": "Thông tin chung về trường, cơ sở vật chất, lịch sử",
                "keywords": ["giới thiệu", "lịch sử", "cơ sở", "thông tin chung", "tầm nhìn", "sứ mệnh", "hoạt động", "campus", "history", "about"]
            }
        }
    
    def classify_content_by_intent(self, content: str, filename: str) -> str:
        """Phân loại nội dung theo intent dựa trên keywords và filename"""
        # Phân loại dựa trên tên file trước
        filename_lower = filename.lower()
        
        # Phân loại theo tên file cụ thể
        if any(keyword in filename_lower for keyword in ["cet", "cit", "cse", "coa", "se", "caf", "cns", "sps", "sl", "sfl", "nganh", "major", "program"]):
            return "nganh_hoc"
        elif any(keyword in filename_lower for keyword in ["daa", "tuyensinh", "admission", "xet-tuyen", "phuong-thuc"]):
            return "xet_tuyen"
        elif any(keyword in filename_lower for keyword in ["dfa", "tai_chinh", "hoc-phi", "tuition", "fee", "scholarship"]):
            return "hoc_phi"
        elif any(keyword in filename_lower for keyword in ["dsa", "lien_he", "contact", "phone", "address"]):
            return "lien_he"
        elif any(keyword in filename_lower for keyword in ["student", "sinh-vien", "club", "activity", "event", "festival"]):
            return "sinh_vien"
        elif any(keyword in filename_lower for keyword in ["research", "nghien-cuu", "khoa-hoc", "publication", "seminar"]):
            return "nghien_cuu"
        elif any(keyword in filename_lower for keyword in ["graduate", "sau-dai-hoc", "thac-si", "tien-si", "master", "phd"]):
            return "sau_dai_hoc"
        elif any(keyword in filename_lower for keyword in ["international", "quoc-te", "cooperation", "exchange", "abroad"]):
            return "quoc_te"
        elif any(keyword in filename_lower for keyword in ["service", "dich-vu", "library", "dormitory", "facility", "medical"]):
            return "dich_vu"
        elif any(keyword in filename_lower for keyword in ["alumni", "cuu-sinh-vien", "career", "job", "employment"]):
            return "cuu_sinh_vien"
        elif any(keyword in filename_lower for keyword in ["publication", "xuat-ban", "journal", "book", "document"]):
            return "xuat_ban"
        
        # Nếu không phân loại được từ filename, dùng content analysis
        content_lower = content.lower()
        best_intent = "thong_tin"  # Default intent
        max_score = 0
        
        for intent_name, intent_info in self.intents.items():
            score = 0
            for keyword in intent_info["keywords"]:
                # Tăng trọng số cho keywords xuất hiện nhiều lần
                keyword_count = content_lower.count(keyword.lower())
                score += keyword_count * (2 if len(keyword) > 5 else 1)  # Từ dài hơn có trọng số cao hơn
            
            # Bonus điểm nếu có nhiều keywords của cùng intent
            keyword_matches = sum(1 for keyword in intent_info["keywords"] if keyword.lower() in content_lower)
            if keyword_matches >= 3:
                score += keyword_matches * 5
            
            if score > max_score:
                max_score = score
                best_intent = intent_name
        
        return best_intent
    
    async def extract_qa_pairs_from_content(self, content: str, intent: str, filename: str) -> List[Dict[str, Any]]:
        """Trích xuất Q&A pairs từ nội dung markdown"""
        if not content.strip() or len(content) < 200:
            return []
        
        intent_info = self.intents[intent]
        
        # Giới hạn độ dài content để tránh vượt quá token limit
        content_chunk = content[:6000] if len(content) > 6000 else content
        
        prompt = f"""
        Bạn là chuyên gia trích xuất dữ liệu cho chatbot tư vấn tuyển sinh Đại học Cần Thơ.
        
        Từ nội dung markdown sau về "{intent_info['description']}" (từ file: {filename}), hãy tạo các cặp câu hỏi-trả lời (Q&A) bằng tiếng Việt:
        
        NỘI DUNG:
        {content_chunk}
        
        YÊU CẦU QUAN TRỌNG:
        1. Tạo 5-15 cặp câu hỏi-trả lời tự nhiên
        2. Câu hỏi phải như sinh viên thật sẽ hỏi (cụ thể, thực tế)
        3. ⚠️ CÂU TRẢ LỜI PHẢI:
           - Trả lời TRỰC TIẾP câu hỏi, không nói "bạn có thể tìm hiểu thêm"
           - Cung cấp thông tin CỤ THỂ từ nội dung (số liệu, mã ngành, tên cụ thể)
           - Nếu không có thông tin trong nội dung thì KHÔNG tạo câu hỏi đó
           - Tránh câu trả lời chung chung như "có nhiều ngành" → phải liệt kê cụ thể
           - Tránh hướng dẫn "liên hệ để biết thêm" → trả lời thẳng thông tin có sẵn
        4. Tập trung vào chủ đề: {intent_info['description']}
        5. Ưu tiên thông tin định lượng: mã ngành, chỉ tiêu, học phí, điểm chuẩn, thời gian
        6. Mỗi câu trả lời phải có ít nhất 1 thông tin cụ thể (số, tên, địa chỉ, ngày tháng)
        
        VÍ DỤ CÁCH TRẢ LỜI TỐT:
        ❌ SAI: "Trường có nhiều ngành học, bạn có thể tham khảo trên website"
        ✅ ĐÚNG: "Trường có các ngành: Công nghệ thông tin (mã 7480201, 300 chỉ tiêu), Kinh tế (mã 7310101, 200 chỉ tiêu), Quản trị kinh doanh (mã 7340101, 250 chỉ tiêu)"
        
        ❌ SAI: "Học phí thay đổi theo từng ngành, liên hệ để biết chi tiết"
        ✅ ĐÚNG: "Học phí năm 2025: Ngành CNTT 15 triệu/năm, Kinh tế 12 triệu/năm, Y khoa 25 triệu/năm"
        
        ❌ SAI: "Có nhiều phương thức xét tuyển"
        ✅ ĐÚNG: "Có 4 phương thức xét tuyển: Điểm thi THPT (70%), Học bạ (20%), Năng khiếu (5%), Ưu tiên khu vực (5%)"
        
        Trả về JSON format:
        {{
            "intent": "{intent}",
            "source_file": "{filename}",
            "qa_pairs": [
                {{
                    "question": "Câu hỏi cụ thể của sinh viên?",
                    "answer": "Câu trả lời CHI TIẾT, CỤ THỂ với số liệu/tên/thông tin định lượng từ nội dung",
                    "category": "{intent}",
                    "confidence": 0.9,
                    "source": "{filename}"
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
                max_tokens=3000
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
            print(f"Error extracting Q&A from {filename}: {e}")
            return []
    
    async def process_crawled_files(self, crawled_dir: str = "output/crawled_ctu_admission_pages"):
        """Xử lý tất cả file markdown đã cào"""
        crawled_path = Path(crawled_dir)
        
        if not crawled_path.exists():
            print(f"❌ Directory not found: {crawled_dir}")
            return
        
        # Lấy tất cả file .md
        md_files = list(crawled_path.glob("*.md"))
        
        if not md_files:
            print(f"❌ No markdown files found in {crawled_dir}")
            return
        
        print(f"🔍 Found {len(md_files)} markdown files to process")
        
        # Tạo thư mục output
        for intent_name, intent_info in self.intents.items():
            folder_path = Path(intent_info["folder"])
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Xử lý từng file
        total_qa_pairs = 0
        intent_counts = {intent: 0 for intent in self.intents.keys()}
        
        for i, md_file in enumerate(md_files, 1):
            print(f"\n📄 Processing {i}/{len(md_files)}: {md_file.name}")
            
            try:
                # Đọc nội dung file
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if len(content) < 200:
                    print(f"   ⚠️ File too short, skipping")
                    continue
                
                # Phân loại intent
                intent = self.classify_content_by_intent(content, md_file.name)
                print(f"   🏷️ Classified as: {intent}")
                
                # Trích xuất Q&A
                qa_pairs = await self.extract_qa_pairs_from_content(content, intent, md_file.name)
                
                if qa_pairs:
                    # Lưu vào file JSON theo intent
                    intent_folder = Path(self.intents[intent]["folder"])
                    output_file = intent_folder / f"{intent}_qa.json"
                    
                    # Merge với dữ liệu cũ nếu có
                    existing_qa_pairs = []
                    if output_file.exists():
                        try:
                            with open(output_file, "r", encoding="utf-8") as f:
                                existing_data = json.load(f)
                            existing_qa_pairs = existing_data.get("qa_pairs", [])
                        except Exception as e:
                            print(f"   ⚠️ Error reading existing file: {e}")
                    
                    # Tạo dữ liệu mới
                    all_qa_pairs = existing_qa_pairs + qa_pairs
                    intent_data = {
                        "intent": intent,
                        "description": self.intents[intent]["description"],
                        "count": len(all_qa_pairs),
                        "qa_pairs": all_qa_pairs,
                        "source": "crawled_markdown_files",
                        "created_date": "2025-01-27",
                        "last_updated": "2025-01-27"
                    }
                    
                    # Lưu file
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(intent_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"   ✅ Extracted {len(qa_pairs)} Q&A pairs → {output_file}")
                    total_qa_pairs += len(qa_pairs)
                    intent_counts[intent] += len(qa_pairs)
                else:
                    print(f"   ❌ No Q&A pairs extracted")
                
            except Exception as e:
                print(f"   ❌ Error processing {md_file.name}: {e}")
        
        # Tạo dataset tổng hợp
        await self.create_combined_dataset(intent_counts, total_qa_pairs)
        
        print(f"\n🎉 Processing completed!")
        print(f"📊 Total Q&A pairs extracted: {total_qa_pairs}")
        print(f"📋 Distribution by intent:")
        for intent, count in intent_counts.items():
            if count > 0:
                print(f"   - {intent}: {count} pairs")
    
    async def create_combined_dataset(self, intent_counts: Dict[str, int], total_qa_pairs: int):
        """Tạo dataset tổng hợp từ tất cả các intent"""
        combined_data = {
            "dataset_info": {
                "name": "CTU Comprehensive QA Dataset - Extended",
                "version": "3.0",
                "description": "Dataset câu hỏi-trả lời tư vấn tuyển sinh Đại học Cần Thơ từ crawled data với 12 intent categories",
                "created_date": "2025-01-27",
                "source": "Extracted from crawled markdown files",
                "total_pairs": total_qa_pairs,
                "total_intents": len(self.intents),
                "intent_list": list(self.intents.keys())
            },
            "intents": intent_counts,
            "qa_pairs": []
        }
        
        # Đọc dữ liệu từ tất cả các intent
        for intent, intent_info in self.intents.items():
            intent_file = Path(intent_info["folder"]) / f"{intent}_qa.json"
            
            if intent_file.exists():
                try:
                    with open(intent_file, "r", encoding="utf-8") as f:
                        intent_data = json.load(f)
                    
                    qa_pairs = intent_data.get("qa_pairs", [])
                    combined_data["qa_pairs"].extend(qa_pairs)
                    
                    print(f"   ✅ Added {len(qa_pairs)} Q&A pairs from {intent}")
                except Exception as e:
                    print(f"   ❌ Error reading {intent_file}: {e}")
        
        # Lưu dataset tổng hợp
        output_file = Path("data/final/ctu_extended_dataset.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Combined dataset saved to: {output_file}")


async def main():
    """Main function"""
    load_dotenv(override=True)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return
    
    print("🚀 Starting extraction from crawled markdown files...")
    
    # Tạo extractor
    extractor = CrawledFilesExtractor(api_key)
    
    # Xử lý tất cả file đã cào
    await extractor.process_crawled_files()
    
    print("\n🎉 Extraction from crawled files completed!")


if __name__ == "__main__":
    asyncio.run(main()) 