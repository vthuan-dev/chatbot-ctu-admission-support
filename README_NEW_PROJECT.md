# 🤖 CTU Admission Chatbot Dataset Project

## 📁 Project Structure (Mới - Đơn giản)

```
CTU_Chatbot/
├── 📁 data/
│   ├── 📁 raw/                    # Dữ liệu thô từ crawl
│   ├── 📁 processed/              # Dữ liệu đã xử lý
│   └── 📁 final/                  # Dataset cuối cùng
├── 📁 scripts/
│   ├── 01_crawl_basic.py          # Crawl cơ bản
│   ├── 02_extract_qa.py           # Extract Q&A
│   ├── 03_organize_by_intent.py   # Tổ chức theo intent
│   └── 04_create_final_dataset.py # Tạo dataset cuối
├── 📁 config/
│   ├── intents.json               # Định nghĩa các intent
│   └── settings.json              # Cấu hình chung
└── 📄 README.md
```

## 🎯 Intent Categories (Đơn giản)

```json
{
  "intents": {
    "nganh_hoc": {
      "name": "Hỏi về ngành học",
      "examples": ["ngành nào", "mã ngành", "chỉ tiêu"]
    },
    "xet_tuyen": {
      "name": "Hỏi xét tuyển", 
      "examples": ["điểm chuẩn", "tổ hợp môn", "phương thức"]
    },
    "hoc_phi": {
      "name": "Hỏi học phí",
      "examples": ["học phí", "học bổng", "chi phí"]
    },
    "lien_he": {
      "name": "Hỏi liên hệ",
      "examples": ["địa chỉ", "số điện thoại", "email"]
    },
    "thong_tin": {
      "name": "Thông tin chung",
      "examples": ["về trường", "cơ sở", "ký túc xá"]
    }
  }
}
```

## 📄 JSON Format (Đơn giản)

### Single Q&A Pair:
```json
{
  "id": "qa_001",
  "question": "Trường có bao nhiêu ngành?",
  "answer": "Trường ĐHCT có 117 ngành đào tạo năm 2025",
  "intent": "nganh_hoc",
  "confidence": 0.9,
  "source_url": "https://tuyensinh.ctu.edu.vn/...",
  "created_date": "2025-01-20"
}
```

### Dataset File:
```json
{
  "dataset_info": {
    "name": "CTU Admission QA Dataset",
    "version": "1.0",
    "total_pairs": 250,
    "created_date": "2025-01-20"
  },
  "intents": {
    "nganh_hoc": 50,
    "xet_tuyen": 60, 
    "hoc_phi": 40,
    "lien_he": 30,
    "thong_tin": 70
  },
  "qa_pairs": [
    {
      "id": "qa_001",
      "question": "...",
      "answer": "...",
      "intent": "nganh_hoc"
    }
  ]
}
```

## 🚀 Workflow Mới (3 bước đơn giản)

### Bước 1: Crawl Data
```bash
python scripts/01_crawl_basic.py
# Output: data/raw/crawled_pages.json
```

### Bước 2: Extract Q&A  
```bash
python scripts/02_extract_qa.py
# Output: data/processed/qa_extracted.json
```

### Bước 3: Organize by Intent
```bash
python scripts/03_organize_by_intent.py  
# Output: data/final/ctu_chatbot_dataset.json
```

## 💡 Ưu điểm Structure Mới

1. **Đơn giản**: Chỉ 3 bước chính
2. **Rõ ràng**: Mỗi file có mục đích cụ thể  
3. **Dễ debug**: JSON structure đơn giản
4. **Dễ mở rộng**: Thêm intent mới dễ dàng
5. **Chuẩn**: Theo best practices

## 🎯 Next Steps

1. Tạo project structure mới
2. Migrate data hiện tại (244 Q&A pairs)
3. Organize theo intent
4. Tạo final dataset
5. Train chatbot model

---
**Bạn có muốn tôi tạo project mới này không?** 