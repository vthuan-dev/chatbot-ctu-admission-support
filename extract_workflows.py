import re
import json
import os

def extract_workflows_from_markdown(md_file_path, json_output_path):
    """
    Trích xuất thông tin workflow từ file markdown n8n.io dựa trên cấu trúc thực tế
    """
    # Đọc file markdown
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm tất cả các workflow dựa vào pattern thực tế
    # Pattern: mô tả[!](avatar_url)tác_giả⋅ngày⋅giá](url)
    pattern = r'([^[\]]*?)\[!\]\((https?://[^)]+)\)([^⋅]+)⋅([^⋅]+)⋅([^\]]+)\]\((https://n8n\.io/workflows/[^)]+)\)'
    
    workflows = []
    matches = re.finditer(pattern, content)
    
    for match in matches:
        # Trích xuất các thành phần
        description = match.group(1).strip()
        avatar_url = match.group(2)
        author = match.group(3).strip()
        date = match.group(4).strip()
        price = match.group(5).strip()
        url = match.group(6)
        
        # Tách tiêu đề và mô tả (nếu có thể)
        title_parts = description.split(' ', 10)  # Lấy tối đa 10 từ đầu tiên làm tiêu đề
        title = ' '.join(title_parts[:10])
        
        workflow = {
            "title": title,
            "description": description,
            "author": author,
            "date": date,
            "price": price,
            "avatar_url": avatar_url,
            "url": url
        }
        
        workflows.append(workflow)
    
    # Lưu dữ liệu đã trích xuất vào file JSON
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(workflows, f, indent=2, ensure_ascii=False)
    
    return len(workflows)

if __name__ == "__main__":
    md_file = "output/https_n8n.io_workflows_categories_ai_.md"
    json_file = "output/n8n_workflows.json"
    
    count = extract_workflows_from_markdown(md_file, json_file)
    print(f"Đã trích xuất thành công {count} workflows và lưu vào {json_file}") 