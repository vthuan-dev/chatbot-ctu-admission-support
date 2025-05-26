import re
import json
import os

def parse_n8n_markdown_to_json(markdown_filepath, json_filepath):
    """
    Parses a specific N8N workflow Markdown file to a JSON dataset.
    """
    try:
        with open(markdown_filepath, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file đầu vào tại {markdown_filepath}")
        return
    except Exception as e:
        print(f"Lỗi khi đọc file đầu vào: {e}")
        return

    # Pattern để tìm workflow, dựa trên cấu trúc thực tế của file
    # Format: text_description[!](avatar_url)author⋅date⋅price](workflow_url)
    workflow_pattern = re.compile(
        r"(.+?)"                              # Group 1: Phần mô tả
        r"\[!\]\((https?://[^)]+)\)"          # Group 2: URL avatar
        r"([^⋅]+)"                            # Group 3: Tác giả
        r"⋅([^⋅]+)"                           # Group 4: Ngày đăng
        r"⋅([^\]]+)\]"                        # Group 5: Giá (Free/Paid)
        r"\((https?://n8n\.io/workflows/[^)]+)\)" # Group 6: URL workflow
    , re.DOTALL)

    extracted_data = []
    
    # Tìm và in ra các section chính trong file để debug
    print("\n--- CÁC SECTION CHÍNH ---")
    section_titles = re.findall(r"#+ ([^\n]+)", markdown_content)
    for i, title in enumerate(section_titles):
        print(f"{i+1}. {title}")
    
    # Tìm section chứa kết quả workflow - bắt đầu từ "## Results"
    results_section_match = re.search(r"## Results \(\d+\)", markdown_content)
    if results_section_match:
        start_pos = results_section_match.end()
        # Lấy nội dung từ "## Results" đến hết file
        content_to_parse = markdown_content[start_pos:]
        print(f"\nĐã tìm thấy section 'Results', bắt đầu phân tích từ vị trí {start_pos}.")
    else:
        content_to_parse = markdown_content
        print("\nCảnh báo: Không tìm thấy section 'Results'. Sẽ phân tích toàn bộ file.")
    
    # In ra một phần nội dung để debug
    print("\n--- ĐOẠN MẪU NỘI DUNG CẦN PHÂN TÍCH ---")
    sample = content_to_parse[:500] if len(content_to_parse) > 500 else content_to_parse
    print(repr(sample))
    
    # Tìm các workflow trong nội dung
    # Đầu tiên, tìm các khớp tổng thể để xem có workflow nào được tìm thấy không
    workflow_matches = re.finditer(
        r"(.*?)\]\((https://n8n\.io/workflows/[^)]+)\)",
        content_to_parse,
        re.DOTALL
    )
    
    simple_matches = []
    for match in workflow_matches:
        description = match.group(1).strip()
        url = match.group(2).strip()
        simple_matches.append({
            "description_snippet": description[:100] + "..." if len(description) > 100 else description,
            "url": url
        })
    
    if simple_matches:
        print(f"\nĐã tìm thấy {len(simple_matches)} khớp tổng thể:")
        for i, match in enumerate(simple_matches[:5]):  # Chỉ hiện 5 kết quả đầu
            print(f"{i+1}. {match['url']} - {match['description_snippet']}")
        
        # Giờ phân tích chi tiết từng workflow
        for item in simple_matches:
            raw_text = item["description_snippet"]
            url = item["url"]
            
            # Tìm thông tin chi tiết (avatar, tác giả, ngày, giá)
            detail_match = re.search(
                r"(.*?)\[!\]\((https?://[^)]+)\)([^⋅]+)⋅([^⋅]+)⋅([^\]]+)$",
                raw_text,
                re.DOTALL
            )
            
            workflow_item = {
                "url": url,
                "raw_text": raw_text
            }
            
            if detail_match:
                workflow_item.update({
                    "title_description": detail_match.group(1).strip(),
                    "avatar_url": detail_match.group(2),
                    "author": detail_match.group(3).strip(),
                    "date_info": detail_match.group(4).strip(),
                    "price_info": detail_match.group(5).strip()
                })
            else:
                workflow_item["parsing_error"] = "Không thể phân tích chi tiết"
            
            extracted_data.append(workflow_item)
    else:
        print("\nKhông tìm thấy workflow nào khớp với pattern.")
    
    try:
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        print(f"\nĐã phân tích dữ liệu thành công và lưu vào {json_filepath}")
        if not extracted_data:
            print("Cảnh báo: Không có dữ liệu nào được trích xuất.")
        else:
            print(f"Đã trích xuất {len(extracted_data)} workflow.")
    except Exception as e:
        print(f"Lỗi khi ghi file JSON đầu ra: {e}")

if __name__ == '__main__':
    input_md_file = "output/https_n8n.io_workflows_categories_ai_.md"
    output_json_file = "output/n8n_workflows_dataset.json"

    if os.path.exists(input_md_file):
        parse_n8n_markdown_to_json(input_md_file, output_json_file)
    else:
        print(f"File đầu vào {input_md_file} không tồn tại.") 