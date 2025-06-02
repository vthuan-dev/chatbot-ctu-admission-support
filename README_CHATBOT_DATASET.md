# CTU Admission Chatbot Dataset Creation Guide

## 📋 Tổng quan

Dự án này xây dựng dataset cho chatbot tư vấn tuyển sinh Đại học Cần Thơ (CTU) với 2 phần chính:
1. **Intent Dataset**: Câu hỏi phân loại theo ý định
2. **Knowledge Base**: Cơ sở tri thức từ website CTU

## 🚀 Quy trình thực hiện

### Phase 1: Thu thập Intent Questions (Tuần 1)

#### Bước 1: Cài đặt môi trường
```bash
# Clone project
git clone <your-repo>
cd ctu-chatbot-dataset

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Thêm OPENAI_API_KEY vào file .env
```

#### Bước 2: Generate Intent Questions
```bash
python 3.intent_questions_generator.py
```

Output:
- `output/intent_dataset/ctu_intent_questions.json`: Dataset câu hỏi theo intent
- `output/intent_dataset/generation_summary.json`: Thống kê generation

**Kết quả mong đợi**:
- 10 intent categories
- ~500-1000 câu hỏi đa dạng
- Bao gồm formal/informal/typo variations

### Phase 2: Crawl Knowledge Base (Tuần 2)

#### Bước 3: Crawl dữ liệu từ CTU
```bash
python 1.crawl.py  # Crawl trang chính
python 4.knowledge_crawler.py  # Crawl chi tiết knowledge
```

Output:
- `output/crawl_result.md`: Raw markdown từ website
- `output/knowledge_base/ctu_knowledge_base.json`: Structured knowledge

#### Bước 4: Extract Q&A từ crawled data
```bash
python 2.llm_extract.py
```

Output:
- `output/processed/*/`: Q&A pairs extracted từ website

### Phase 3: Integration & Mapping (3-4 ngày)

#### Bước 5: Map Intent với Knowledge
```bash
python 5.intent_knowledge_mapper.py
```

Output:
- `output/intent_knowledge_mapping.json`: Mapping rules

## 📁 Cấu trúc dữ liệu

### Intent Dataset Structure
```json
{
  "metadata": {...},
  "intent_categories": [
    {
      "intent_id": "ask_program_fee",
      "intent_name": "Hỏi học phí",
      "keywords": ["học phí", "chi phí"],
      "questions": [
        {
          "text": "Học phí ngành CNTT là bao nhiêu?",
          "entities": ["program_name"],
          "confidence": 0.9
        }
      ]
    }
  ]
}
```

### Knowledge Base Structure
```json
{
  "metadata": {...},
  "data": {
    "programs": [
      {
        "program_code": "7480201",
        "program_name": "Công nghệ thông tin",
        "tuition_fee": "15.2 triệu/năm",
        "duration": "4 năm"
      }
    ],
    "contact_info": {...},
    "facilities": [...]
  }
}
```

## 🎯 Intent Categories

1. **ask_program_fee**: Hỏi học phí
2. **ask_program_duration**: Hỏi thời gian đào tạo
3. **ask_admission_score**: Hỏi điểm chuẩn
4. **ask_admission_method**: Hỏi phương thức xét tuyển
5. **ask_program_info**: Hỏi thông tin ngành
6. **ask_scholarship**: Hỏi học bổng
7. **ask_dormitory**: Hỏi ký túc xá
8. **ask_enrollment_process**: Hỏi thủ tục nhập học
9. **ask_contact_info**: Hỏi thông tin liên hệ
10. **ask_campus_location**: Hỏi vị trí cơ sở

## 🔧 Tùy chỉnh

### Thêm Intent mới
Sửa file `3.intent_questions_generator.py`:
```python
CTU_INTENT_CATEGORIES.append({
    "intent_id": "ask_new_intent",
    "intent_name": "Tên intent",
    "keywords": ["từ khóa"],
    "seed_patterns": ["Mẫu câu hỏi {entity}"]
})
```

### Thêm Knowledge Source
Sửa file `4.knowledge_crawler.py`:
```python
self.crawl_targets["new_source"] = [
    "https://url-to-crawl.com"
]
```

## 📊 Monitoring & Validation

### Kiểm tra chất lượng Intent
```bash
python validate_intents.py
```

### Kiểm tra coverage Knowledge
```bash
python validate_knowledge.py
```

## 🚨 Lưu ý quan trọng

1. **API Rate Limits**: 
   - OpenAI: Max 60 requests/min
   - Add delays between requests

2. **Crawling Ethics**:
   - Respect robots.txt
   - Add delays (2-3s) between requests
   - Don't overload server

3. **Data Quality**:
   - Review generated questions
   - Validate extracted knowledge
   - Test mapping accuracy

## 📈 Next Steps

1. **Training Intent Classifier**:
   - Use generated questions to train classifier
   - Fine-tune on real user queries

2. **Implement RAG System**:
   - Index knowledge base
   - Implement retrieval logic
   - Connect with LLM for generation

3. **Deploy Chatbot**:
   - Setup API endpoints
   - Implement chat interface
   - Monitor performance

## 🤝 Contributing

1. Fork project
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

MIT License - see LICENSE file

## 📞 Support

- Email: your-email@example.com
- Issues: GitHub Issues
- Docs: /docs folder 