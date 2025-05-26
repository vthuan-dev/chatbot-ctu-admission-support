import json
from datetime import datetime

def convert_to_training_format(input_file, output_file):
    """
    Chuyển đổi dữ liệu extracted thành format training cho chatbot
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = {
        "conversations": [],
        "metadata": {
            "total_conversations": 0,
            "categories": set(),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "source": "CTU Admission Website",
            "version": "1.0"
        }
    }
    
    conversation_id = 1
    
    # Xử lý từng chunk data
    for chunk in data:
        if 'qa_pairs' in chunk and chunk['qa_pairs']:
            for qa in chunk['qa_pairs']:
                conversation = {
                    "id": f"ctu_{conversation_id:03d}",
                    "question": qa['question'],
                    "answer": qa['answer'],
                    "category": qa['category'],
                    "intent": f"hoi_{qa['category']}",
                    "priority": qa['priority'],
                    "entities": extract_entities_from_qa(qa),
                    "source": "https://tuyensinh.ctu.edu.vn/"
                }
                
                training_data["conversations"].append(conversation)
                training_data["metadata"]["categories"].add(qa['category'])
                conversation_id += 1
        
        # Thêm thông tin từ structured data
        if 'contact_info' in chunk and chunk['contact_info']:
            contact = chunk['contact_info']
            if contact.get('phone') or contact.get('email'):
                conversation = {
                    "id": f"ctu_{conversation_id:03d}",
                    "question": "Thông tin liên hệ tư vấn tuyển sinh là gì?",
                    "answer": format_contact_info(contact),
                    "category": "lien_he",
                    "intent": "hoi_lien_he",
                    "priority": 1,
                    "entities": {
                        "phone": contact.get('phone'),
                        "email": contact.get('email'),
                        "address": contact.get('address')
                    },
                    "source": "https://tuyensinh.ctu.edu.vn/"
                }
                training_data["conversations"].append(conversation)
                training_data["metadata"]["categories"].add("lien_he")
                conversation_id += 1
        
        # Thêm thông tin ngành học
        if 'majors' in chunk and chunk['majors']:
            for major in chunk['majors']:
                conversation = {
                    "id": f"ctu_{conversation_id:03d}",
                    "question": f"Mã ngành {major['name']} là gì?",
                    "answer": f"Mã ngành {major['name']} là {major['code']}.",
                    "category": "nganh_hoc",
                    "intent": "hoi_ma_nganh",
                    "priority": 2,
                    "entities": {
                        "major_name": major['name'],
                        "major_code": major['code']
                    },
                    "source": "https://tuyensinh.ctu.edu.vn/"
                }
                training_data["conversations"].append(conversation)
                training_data["metadata"]["categories"].add("nganh_hoc")
                conversation_id += 1
    
    # Cập nhật metadata
    training_data["metadata"]["total_conversations"] = len(training_data["conversations"])
    training_data["metadata"]["categories"] = list(training_data["metadata"]["categories"])
    
    # Lưu file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    return training_data

def extract_entities_from_qa(qa):
    """Trích xuất entities từ Q&A"""
    entities = {}
    
    question = qa['question'].lower()
    answer = qa['answer'].lower()
    
    # Trích xuất số lượng
    import re
    numbers = re.findall(r'(\d+)', answer)
    if numbers:
        if 'ngành' in answer:
            entities['total_majors'] = numbers[0]
        elif 'phương thức' in answer:
            entities['total_methods'] = numbers[0]
    
    # Trích xuất năm
    years = re.findall(r'(20\d{2})', answer)
    if years:
        entities['year'] = years[0]
    
    return entities

def format_contact_info(contact):
    """Format thông tin liên hệ thành câu trả lời tự nhiên"""
    parts = []
    
    if contact.get('phone'):
        parts.append(f"Điện thoại: {contact['phone']}")
    
    if contact.get('email'):
        parts.append(f"Email: {contact['email']}")
    
    if contact.get('address'):
        parts.append(f"Địa chỉ: {contact['address']}")
    
    if contact.get('social_media') and contact['social_media'].get('Facebook'):
        parts.append(f"Facebook: {contact['social_media']['Facebook']}")
    
    return "Phòng Đào tạo - Trường Đại học Cần Thơ. " + ". ".join(parts) + "."

def main():
    input_file = "output/https_tuyensinh.ctu.edu.vn_.json"
    output_file = "output/ctu_chatbot_training_data.json"
    
    print("Đang chuyển đổi dữ liệu sang format training...")
    
    training_data = convert_to_training_format(input_file, output_file)
    
    print(f"✅ Hoàn thành!")
    print(f"📁 File output: {output_file}")
    print(f"📊 Thống kê:")
    print(f"   - Tổng conversations: {training_data['metadata']['total_conversations']}")
    print(f"   - Categories: {', '.join(training_data['metadata']['categories'])}")
    print(f"   - Ngày tạo: {training_data['metadata']['created_date']}")

if __name__ == "__main__":
    main() 