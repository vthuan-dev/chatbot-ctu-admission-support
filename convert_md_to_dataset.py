import json
import re
from datetime import datetime

def extract_qa_from_markdown(md_file_path):
    """
    Chuyển đổi file markdown crawl thành dataset JSON có cấu trúc
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    conversations = []
    
    # Trích xuất thông tin từ FAQ section
    faq_pattern = r'#### (.+?) \+\n\n(.+?) \[→ Xem chi tiết\]'
    faq_matches = re.findall(faq_pattern, content, re.DOTALL)
    
    for i, (question, answer) in enumerate(faq_matches):
        conversation = {
            "id": f"ctu_faq_{i+1:03d}",
            "question": question.strip(),
            "answer": answer.strip(),
            "category": "cau_hoi_pho_bien",
            "intent": "hoi_thong_tin_chung",
            "entities": extract_entities(question, answer),
            "source": "https://tuyensinh.ctu.edu.vn/",
            "priority": 1
        }
        conversations.append(conversation)
    
    # Trích xuất thông tin liên hệ
    contact_pattern = r'### Liên hệ tư vấn tuyển sinh đại học chính quy\n\n(.+?)(?=\n\n|\n-|$)'
    contact_match = re.search(contact_pattern, content, re.DOTALL)
    
    if contact_match:
        contact_info = contact_match.group(1).strip()
        conversation = {
            "id": "ctu_contact_001",
            "question": "Thông tin liên hệ tư vấn tuyển sinh là gì?",
            "answer": contact_info,
            "category": "lien_he",
            "intent": "hoi_lien_he",
            "entities": extract_contact_entities(contact_info),
            "source": "https://tuyensinh.ctu.edu.vn/",
            "priority": 1
        }
        conversations.append(conversation)
    
    # Trích xuất thông tin ngành học
    major_pattern = r'## \[ (.+?) \].*?Mã ngành:\s*(\d+)'
    major_matches = re.findall(major_pattern, content, re.DOTALL)
    
    for i, (major_name, major_code) in enumerate(major_matches):
        conversation = {
            "id": f"ctu_major_{i+1:03d}",
            "question": f"Ngành {major_name} có mã ngành là gì?",
            "answer": f"Ngành {major_name} có mã ngành {major_code}.",
            "category": "thong_tin_nganh",
            "intent": "hoi_ma_nganh",
            "entities": {
                "major_name": major_name,
                "major_code": major_code
            },
            "source": "https://tuyensinh.ctu.edu.vn/",
            "priority": 2
        }
        conversations.append(conversation)
    
    return conversations

def extract_entities(question, answer):
    """Trích xuất entities từ câu hỏi và câu trả lời"""
    entities = {}
    
    # Trích xuất năm
    year_pattern = r'(\d{4})'
    years = re.findall(year_pattern, question + " " + answer)
    if years:
        entities["year"] = years[0]
    
    # Trích xuất số lượng
    number_pattern = r'(\d+)\s*(ngành|phương thức|mã)'
    numbers = re.findall(number_pattern, answer, re.IGNORECASE)
    for number, unit in numbers:
        if 'ngành' in unit:
            entities["total_majors"] = number
        elif 'phương thức' in unit:
            entities["total_methods"] = number
    
    return entities

def extract_contact_entities(contact_text):
    """Trích xuất thông tin liên hệ"""
    entities = {}
    
    # Trích xuất số điện thoại
    phone_pattern = r'Điện thoại:\s*([\d\.\s]+)'
    phone_match = re.search(phone_pattern, contact_text)
    if phone_match:
        entities["phone"] = phone_match.group(1).strip()
    
    # Trích xuất mobile
    mobile_pattern = r'Mobile/Zalo/Viber:\s*([\d]+)'
    mobile_match = re.search(mobile_pattern, contact_text)
    if mobile_match:
        entities["mobile"] = mobile_match.group(1)
    
    # Trích xuất email
    email_pattern = r'Email:\s*([\w\.-]+@[\w\.-]+)'
    email_match = re.search(email_pattern, contact_text)
    if email_match:
        entities["email"] = email_match.group(1)
    
    # Trích xuất địa chỉ
    address_pattern = r'Địa chỉ:\s*([^-]+)'
    address_match = re.search(address_pattern, contact_text)
    if address_match:
        entities["address"] = address_match.group(1).strip()
    
    return entities

def create_dataset(conversations):
    """Tạo dataset hoàn chỉnh với metadata"""
    categories = list(set([conv["category"] for conv in conversations]))
    intents = list(set([conv["intent"] for conv in conversations]))
    
    dataset = {
        "conversations": conversations,
        "metadata": {
            "total_conversations": len(conversations),
            "categories": categories,
            "intents": intents,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "source_website": "https://tuyensinh.ctu.edu.vn/",
            "version": "1.0"
        }
    }
    
    return dataset

def main():
    # Chuyển đổi file markdown thành dataset
    md_file = "output/crawl_result.md"
    output_file = "output/ctu_chatbot_dataset.json"
    
    print("Đang chuyển đổi markdown thành dataset...")
    conversations = extract_qa_from_markdown(md_file)
    
    print(f"Đã trích xuất {len(conversations)} conversations")
    
    # Tạo dataset hoàn chỉnh
    dataset = create_dataset(conversations)
    
    # Lưu dataset
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"Dataset đã được lưu tại: {output_file}")
    
    # Hiển thị thống kê
    print(f"\nThống kê dataset:")
    print(f"- Tổng số conversations: {dataset['metadata']['total_conversations']}")
    print(f"- Số categories: {len(dataset['metadata']['categories'])}")
    print(f"- Số intents: {len(dataset['metadata']['intents'])}")
    print(f"- Categories: {', '.join(dataset['metadata']['categories'])}")

if __name__ == "__main__":
    main() 