import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai


class PDFMarkdownExtractor:
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.intents = {
            "thong_tin_nganh": {
                "folder": "data/processed/thong_tin_nganh",
                "description": "Thông tin chung về ngành học",
                "keywords": ["ngành", "chuyên ngành", "đào tạo", "mã ngành", "chỉ tiêu", "tuyển sinh", "giới thiệu ngành"]
            },
            "chuong_trinh_dao_tao": {
                "folder": "data/processed/chuong_trinh_dao_tao",
                "description": "Chi tiết chương trình đào tạo",
                "keywords": ["chương trình", "khung chương trình", "ctđt", "curriculum", "syllabus", "khóa học"]
            },
            "mon_hoc": {
                "folder": "data/processed/mon_hoc",
                "description": "Thông tin về môn học, học phần",
                "keywords": ["môn học", "học phần", "tín chỉ", "môn bắt buộc", "môn tự chọn", "điều kiện tiên quyết"]
            },
            "phuong_phap_giang_day": {
                "folder": "data/processed/phuong_phap_giang_day",
                "description": "Phương pháp giảng dạy, hình thức học",
                "keywords": ["giảng dạy", "phương pháp", "dạy học", "lý thuyết", "thực hành", "seminar", "đồ án"]
            },
            "danh_gia": {
                "folder": "data/processed/danh_gia",
                "description": "Phương pháp đánh giá, kiểm tra",
                "keywords": ["đánh giá", "kiểm tra", "thi", "bài tập", "điểm", "thang điểm", "trọng số"]
            },
            "co_so_vat_chat": {
                "folder": "data/processed/co_so_vat_chat",
                "description": "Cơ sở vật chất phục vụ đào tạo",
                "keywords": ["phòng học", "phòng thí nghiệm", "trang thiết bị", "cơ sở vật chất", "phòng máy", "thư viện"]
            },
            "giang_vien": {
                "folder": "data/processed/giang_vien",
                "description": "Đội ngũ giảng viên",
                "keywords": ["giảng viên", "giáo viên", "thạc sĩ", "tiến sĩ", "phó giáo sư", "giáo sư", "trình độ"]
            },
            "chuan_dau_ra": {
                "folder": "data/processed/chuan_dau_ra",
                "description": "Chuẩn đầu ra của chương trình",
                "keywords": ["chuẩn đầu ra", "kết quả học tập", "năng lực", "kỹ năng", "thái độ", "kiến thức", "PLO"]
            },
            "co_hoi_nghe_nghiep": {
                "folder": "data/processed/co_hoi_nghe_nghiep",
                "description": "Cơ hội việc làm, nghề nghiệp",
                "keywords": ["việc làm", "nghề nghiệp", "cơ hội", "vị trí", "doanh nghiệp", "thị trường", "career"]
            },
            "hoc_phi": {
                "folder": "data/processed/hoc_phi",
                "description": "Học phí và các khoản phí",
                "keywords": ["học phí", "lệ phí", "chi phí", "đóng tiền", "miễn giảm", "học bổng"]
            },
            "quy_che": {
                "folder": "data/processed/quy_che",
                "description": "Quy chế, quy định đào tạo",
                "keywords": ["quy chế", "quy định", "điều kiện", "yêu cầu", "bắt buộc", "tốt nghiệp", "học vụ"]
            },
            "thuc_tap": {
                "folder": "data/processed/thuc_tap",
                "description": "Thực tập, thực tế",
                "keywords": ["thực tập", "thực tế", "kiến tập", "doanh nghiệp", "đồ án", "project", "internship"]
            }
        }
    
    async def extract_qa_from_markdown(self, markdown_path: str) -> List[Dict[str, Any]]:
        """Trích xuất Q&A từ file markdown"""
        print(f"📄 Processing markdown file: {markdown_path}")
        
        try:
            # Đọc nội dung markdown
            with open(markdown_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if len(content) < 200:
                print("   ⚠️ Content too short")
                return []
            
            # Phân loại nội dung
            intent = self.classify_content(content)
            print(f"   🏷️ Classified as: {intent}")
            
            # Trích xuất Q&A
            qa_pairs = await self.extract_qa_pairs(content, intent, Path(markdown_path).name)
            
            if qa_pairs:
                # Lưu vào file JSON theo intent
                intent_folder = Path(self.intents[intent]["folder"])
                intent_folder.mkdir(parents=True, exist_ok=True)
                output_file = intent_folder / f"{intent}_qa_from_pdf.json"
                
                # Tạo dữ liệu mới
                intent_data = {
                    "intent": intent,
                    "description": self.intents[intent]["description"],
                    "count": len(qa_pairs),
                    "qa_pairs": qa_pairs,
                    "source": "pdf_markdown",
                    "source_file": Path(markdown_path).name,
                    "created_date": "2025-01-27",
                    "last_updated": "2025-01-27"
                }
                
                # Lưu file
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(intent_data, f, indent=2, ensure_ascii=False)
                
                print(f"   ✅ Extracted {len(qa_pairs)} Q&A pairs → {output_file}")
                return qa_pairs
            
            else:
                print("   ❌ No Q&A pairs extracted")
                return []
            
        except Exception as e:
            print(f"   ❌ Error processing file: {e}")
            return []
    
    def classify_content(self, content: str) -> str:
        """Phân loại nội dung theo intent dựa trên keywords"""
        content_lower = content.lower()
        best_intent = "nganh_hoc"  # Default intent
        max_score = 0
        
        for intent_name, intent_info in self.intents.items():
            score = 0
            for keyword in intent_info["keywords"]:
                keyword_count = content_lower.count(keyword.lower())
                score += keyword_count * (2 if len(keyword) > 5 else 1)
            
            keyword_matches = sum(1 for keyword in intent_info["keywords"] if keyword.lower() in content_lower)
            if keyword_matches >= 3:
                score += keyword_matches * 5
            
            if score > max_score:
                max_score = score
                best_intent = intent_name
        
        return best_intent
    
    async def extract_qa_pairs(self, content: str, intent: str, filename: str) -> List[Dict[str, Any]]:
        """Trích xuất Q&A pairs từ nội dung"""
        intent_info = self.intents[intent]
        
        # Giới hạn độ dài content
        content_chunk = content[:15000] if len(content) > 15000 else content

        # Tạo prompt tùy theo intent
        base_prompt = f"""
        Bạn là chuyên gia tư vấn tuyển sinh của Trường Đại học Cần Thơ (CTU).
        Từ nội dung về "{intent_info['description']}" (file: {filename}), hãy tạo các cặp hỏi-đáp CHẤT LƯỢNG CAO.

        NỘI DUNG:
        {content_chunk}
        """

        # Thêm yêu cầu chi tiết theo từng intent
        if intent == "thong_tin_nganh":
            prompt = base_prompt + """
            YÊU CẦU QUAN TRỌNG:
            1. Tạo 15-20 cặp hỏi đáp về ngành học, tập trung vào:
               - Mã ngành, tên ngành (tiếng Việt & tiếng Anh)
               - Chỉ tiêu tuyển sinh
               - Điểm chuẩn các năm trước (nếu có)
               - Tổ hợp xét tuyển
               - Thời gian đào tạo
               - Văn bằng tốt nghiệp
               - Điểm đặc thù của ngành

            2. Câu hỏi PHẢI:
               - Đặt như sinh viên/phụ huynh thật sẽ hỏi
               - Cụ thể và thực tế
               - Đa dạng góc độ (học tập, cơ hội việc làm, đặc thù ngành...)
               
            3. Câu trả lời PHẢI:
               - Chính xác 100% theo nội dung
               - Đầy đủ thông tin định lượng (số liệu, mã ngành, điểm...)
               - Cấu trúc rõ ràng, dễ đọc
               - KHÔNG dùng câu "bạn có thể tham khảo thêm..."
               - KHÔNG chung chung, phải nêu cụ thể

            VÍ DỤ CÂU HỎI TỐT:
            - "Ngành X có mã ngành là gì và xét tuyển những tổ hợp nào?"
            - "Em muốn học ngành X thì cần chuẩn bị những gì? Điểm chuẩn mấy năm gần đây thế nào?"
            - "Học ngành X có những môn học chính nào? Có nhiều thực hành không ạ?"
            """

        elif intent == "chuong_trinh_dao_tao":
            prompt = base_prompt + """
            YÊU CẦU QUAN TRỌNG:
            1. Tạo 15-20 cặp hỏi đáp về chương trình đào tạo, tập trung:
               - Cấu trúc chương trình
               - Số tín chỉ tổng và từng khối kiến thức
               - Thời gian đào tạo
               - Các học phần quan trọng
               - Lộ trình học tập
               - Điều kiện tốt nghiệp

            2. Câu trả lời PHẢI:
               - Liệt kê đầy đủ số tín chỉ
               - Nêu rõ các môn học theo từng khối kiến thức
               - Giải thích chi tiết yêu cầu và điều kiện
            """

        elif intent == "mon_hoc":
            prompt = base_prompt + """
            YÊU CẦU QUAN TRỌNG:
            1. Tạo 15-20 cặp hỏi đáp về môn học, tập trung:
               - Tên và mã môn học
               - Số tín chỉ của môn
               - Điều kiện tiên quyết
               - Nội dung môn học
               - Phương pháp đánh giá
               - Tài liệu học tập

            2. Câu trả lời PHẢI:
               - Nêu đầy đủ thông tin về môn học
               - Giải thích rõ cách tính điểm, đánh giá
               - Liệt kê tài liệu học tập chính
            """

        elif intent == "co_hoi_nghe_nghiep":
            prompt = base_prompt + """
            YÊU CẦU QUAN TRỌNG:
            1. Tạo 15-20 cặp hỏi đáp về cơ hội nghề nghiệp, tập trung:
               - Vị trí việc làm có thể đảm nhận
               - Các công ty/đơn vị tuyển dụng
               - Mức lương tham khảo (nếu có)
               - Khả năng thăng tiến
               - Xu hướng nghề nghiệp
               - Kỹ năng cần thiết

            2. Câu trả lời PHẢI:
               - Liệt kê cụ thể vị trí công việc
               - Nêu tên công ty/lĩnh vực cụ thể
               - Đề cập đến yêu cầu thực tế của nhà tuyển dụng
            """

        else:
            # Prompt mặc định cho các intent khác
            prompt = base_prompt + """
            YÊU CẦU QUAN TRỌNG:
            1. Tạo 15-20 cặp hỏi đáp chất lượng cao
            2. Câu hỏi phải:
               - Thực tế, cụ thể
               - Đúng trọng tâm chủ đề
               - Đa dạng góc độ
            3. Câu trả lời phải:
               - Chính xác theo nội dung
               - Đầy đủ thông tin định lượng
               - Cấu trúc rõ ràng
               - Không chung chung
            """

        prompt += """
        Trả về JSON format:
        {
            "intent": "%s",
            "source_file": "%s",
            "qa_pairs": [
                {
                    "question": "Câu hỏi thực tế của sinh viên?",
                    "answer": "Câu trả lời CHI TIẾT với thông tin cụ thể từ nội dung",
                    "category": "%s",
                    "confidence": 0.9
                }
            ]
        }
        """ % (intent, filename, intent)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia tư vấn tuyển sinh CTU, luôn tạo câu hỏi và trả lời THỰC TẾ, CỤ THỂ, và CHÍNH XÁC."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Giảm temperature để tăng tính chính xác
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result = json.loads(result_text.strip())
            return result.get("qa_pairs", [])
            
        except Exception as e:
            print(f"   ❌ Error extracting Q&A: {e}")
            return []


async def main():
    """Main function"""
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found in .env file")
        return
    
    print("🚀 Starting PDF markdown extraction...")
    
    # Khởi tạo extractor
    extractor = PDFMarkdownExtractor(api_key)
    
    # Xử lý file markdown từ PDF
    markdown_file = "output/pdf_extracted.md"
    if not os.path.exists(markdown_file):
        print(f"❌ Markdown file not found: {markdown_file}")
        return
    
    qa_pairs = await extractor.extract_qa_from_markdown(markdown_file)
    
    print(f"\n🎉 Extraction completed!")
    print(f"📊 Total Q&A pairs extracted: {len(qa_pairs)}")


if __name__ == "__main__":
    asyncio.run(main()) 