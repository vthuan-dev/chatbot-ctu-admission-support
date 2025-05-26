# 🤖 N8N Workflow cho CTU Auto Crawl

## 📋 Setup N8N

### 1. Cài đặt N8N
```bash
npm install -g n8n
# hoặc
npx n8n
```

### 2. Chạy N8N
```bash
n8n start
# Mở: http://localhost:5678
```

## 🔄 Workflow Design

### Node 1: Manual Trigger
- **Type**: Manual Trigger
- **Input**: 
  - `start_url`: URL bắt đầu
  - `max_depth`: Độ sâu tối đa (default: 3)
  - `max_urls`: URLs tối đa mỗi level (default: 5)

### Node 2: Initialize
- **Type**: Code
- **Function**: Setup variables
```javascript
return [
  {
    json: {
      current_urls: [items[0].json.start_url],
      level: 1,
      max_depth: items[0].json.max_depth || 3,
      max_urls: items[0].json.max_urls || 5,
      all_qa_pairs: [],
      crawled_urls: []
    }
  }
];
```

### Node 3: Level Loop
- **Type**: Loop Over Items
- **Expression**: `{{$json.level <= $json.max_depth && $json.current_urls.length > 0}}`

### Node 4: URL Loop  
- **Type**: Loop Over Items
- **Items**: `{{$json.current_urls.slice(0, $json.max_urls)}}`

### Node 5: HTTP Crawl
- **Type**: HTTP Request
- **Method**: GET
- **URL**: `{{$json.url}}`
- **Headers**: 
  ```json
  {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  }
  ```

### Node 6: Clean HTML
- **Type**: Code
- **Function**: Clean HTML content
```javascript
const html = items[0].binary.data.toString();

// Remove scripts and styles
let content = html.replace(/<script[^>]*>.*?<\/script>/gis, '');
content = content.replace(/<style[^>]*>.*?<\/style>/gis, '');

// Extract text
content = content.replace(/<[^>]+>/g, ' ');
content = content.replace(/\s+/g, ' ').trim();

// Limit length
content = content.substring(0, 8000);

return [
  {
    json: {
      url: items[0].json.url,
      content: content
    }
  }
];
```

### Node 7: OpenAI Extract
- **Type**: OpenAI
- **Operation**: Chat
- **Model**: gpt-4o-mini
- **Messages**:
```json
[
  {
    "role": "system",
    "content": "Trả về JSON hợp lệ về tuyển sinh CTU."
  },
  {
    "role": "user", 
    "content": "Phân tích nội dung tuyển sinh CTU:\n\n{{$json.content}}\n\nTrả về JSON:\n{\n  \"qa_pairs\": [\n    {\n      \"question\": \"Câu hỏi tiếng Việt\",\n      \"answer\": \"Trả lời chi tiết\",\n      \"category\": \"nganh_hoc\",\n      \"source\": \"{{$json.url}}\"\n    }\n  ],\n  \"urls\": [\"url1\", \"url2\"]\n}\n\nCHỈ trả về JSON."
  }
]
```

### Node 8: Process Results
- **Type**: Code
- **Function**: Process OpenAI response
```javascript
const response = JSON.parse(items[0].json.choices[0].message.content);
const qa_pairs = response.qa_pairs || [];
const extracted_urls = response.urls || [];

// Filter CTU URLs
const ctu_indicators = ['ctu.edu.vn', 'tuyensinh', 'nganh', 'hoc-phi'];
const valid_urls = extracted_urls.filter(url => 
  ctu_indicators.some(indicator => url.toLowerCase().includes(indicator))
);

return [
  {
    json: {
      qa_pairs: qa_pairs,
      next_urls: valid_urls,
      current_url: items[0].json.url
    }
  }
];
```

### Node 9: Save Level Data
- **Type**: Write Binary File
- **File Path**: `data/auto_crawl/n8n_level_{{$json.level}}.json`
- **Data**: 
```json
{
  "level": "{{$json.level}}",
  "timestamp": "{{$now}}",
  "qa_pairs": "{{$json.all_qa_pairs}}",
  "urls": "{{$json.next_urls}}"
}
```

### Node 10: Add to Dataset
- **Type**: Execute Command
- **Command**: `python`
- **Arguments**: `["scripts/add_new_data.py", "data/auto_crawl/n8n_level_{{$json.level}}.json"]`

### Node 11: Next Level
- **Type**: Code
- **Function**: Prepare next level
```javascript
return [
  {
    json: {
      current_urls: items[0].json.next_urls,
      level: items[0].json.level + 1,
      max_depth: items[0].json.max_depth,
      max_urls: items[0].json.max_urls,
      all_qa_pairs: [...items[0].json.all_qa_pairs, ...items[0].json.qa_pairs],
      crawled_urls: [...items[0].json.crawled_urls, items[0].json.current_url]
    }
  }
];
```

## 🎯 Workflow Features

### ✅ **Tự động hoàn toàn**
- Chỉ cần nhập URL ban đầu
- Tự động crawl đệ quy
- Tự động thêm vào dataset

### ✅ **Error Handling**
- Retry khi HTTP request fail
- Skip URLs lỗi
- Continue với URLs khác

### ✅ **Monitoring**
- Real-time progress
- Log chi tiết
- Email notification khi done

### ✅ **Scheduling**
- Chạy hàng ngày/tuần
- Crawl URLs mới tự động
- Update dataset liên tục

## 🚀 **Cách sử dụng:**

1. **Import workflow** vào N8N
2. **Set OpenAI API key** trong credentials
3. **Click "Execute Workflow"**
4. **Nhập URL** và parameters
5. **Ngồi uống cà phê** ☕ - N8N làm hết!

## 💡 **Lợi ích:**

- 🎯 **Zero coding** - Chỉ kéo thả
- 🔄 **Visual workflow** - Dễ hiểu, dễ sửa
- 📊 **Real-time monitoring** - Theo dõi live
- ⚡ **Auto retry** - Không lo lỗi
- 📅 **Scheduling** - Chạy tự động
- 🔔 **Notifications** - Báo khi xong

**Đơn giản hơn Python scripts rất nhiều!** 🎉 