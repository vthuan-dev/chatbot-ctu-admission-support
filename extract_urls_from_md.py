import re
import json
from pathlib import Path

def extract_urls_from_markdown(md_file_path):
    """
    Extract URLs from markdown file and categorize them by intent
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract all URLs using regex
    url_pattern = r'https://tuyensinh\.ctu\.edu\.vn[^\s\)\]]*'
    urls = re.findall(url_pattern, content)
    
    # Remove duplicates and clean URLs
    unique_urls = list(set(urls))
    cleaned_urls = []
    
    for url in unique_urls:
        # Remove trailing punctuation
        url = re.sub(r'[,\.\)\]\s]+$', '', url)
        if url not in cleaned_urls:
            cleaned_urls.append(url)
    
    return cleaned_urls

def categorize_urls_by_intent(urls):
    """
    Categorize URLs by intent based on URL patterns and content
    """
    categorized = {
        "hoi_nganh_hoc": [],
        "hoi_phuong_thuc_xet_tuyen": [],
        "hoi_hoc_phi": [],
        "hoi_lien_he": [],
        "hoi_thong_tin_chung": []
    }
    
    for url in urls:
        url_lower = url.lower()
        
        # Categorize based on URL patterns
        if any(keyword in url_lower for keyword in [
            'nganh', 'major', 'chuyen-nganh', 'gioi-thieu-nganh', 
            'danh-muc-nganh', 'chi-tieu', 'tien-tien', 'chat-luong-cao'
        ]):
            categorized["hoi_nganh_hoc"].append(url)
            
        elif any(keyword in url_lower for keyword in [
            'phuong-thuc', 'xet-tuyen', 'tuyen-thang', 'hoc-ba', 
            'thpt', 'vsat', 'v-sat', 'uu-tien'
        ]):
            categorized["hoi_phuong_thuc_xet_tuyen"].append(url)
            
        elif any(keyword in url_lower for keyword in [
            'hoc-phi', 'hoc-bong', 'tuition', 'scholarship', 'ho-tro'
        ]):
            categorized["hoi_hoc_phi"].append(url)
            
        elif any(keyword in url_lower for keyword in [
            'lien-he', 'contact', 'tu-van', 'dia-chi', 'phone', 'email'
        ]):
            categorized["hoi_lien_he"].append(url)
            
        else:
            # Default to general information
            categorized["hoi_thong_tin_chung"].append(url)
    
    return categorized

def create_crawl_structure_from_urls(categorized_urls):
    """
    Create CRAWL_STRUCTURE from categorized URLs
    """
    structure = {}
    
    # Define intent descriptions and prompts
    intent_config = {
        "hoi_nganh_hoc": {
            "description": "Câu hỏi về ngành học",
            "base_prompt": "Extract major information, codes, requirements, and create Q&A pairs about academic programs in Vietnamese."
        },
        "hoi_phuong_thuc_xet_tuyen": {
            "description": "Câu hỏi về phương thức xét tuyển", 
            "base_prompt": "Extract admission methods, requirements, deadlines, and create Q&A pairs about admission processes in Vietnamese."
        },
        "hoi_hoc_phi": {
            "description": "Câu hỏi về học phí",
            "base_prompt": "Extract tuition fees, payment methods, scholarships, and create Q&A pairs about costs in Vietnamese."
        },
        "hoi_lien_he": {
            "description": "Câu hỏi về liên hệ",
            "base_prompt": "Extract contact information, office hours, locations, and create Q&A pairs about contact details in Vietnamese."
        },
        "hoi_thong_tin_chung": {
            "description": "Câu hỏi thông tin chung",
            "base_prompt": "Extract general admission information, announcements, and create Q&A pairs about general topics in Vietnamese."
        }
    }
    
    for intent, urls in categorized_urls.items():
        if not urls:
            continue
            
        structure[intent] = {
            "description": intent_config[intent]["description"],
            "targets": []
        }
        
        # Create targets from URLs
        for i, url in enumerate(urls[:5], 1):  # Limit to 5 URLs per intent
            # Generate filename from URL
            filename_parts = url.split('/')[-1].split('.')[0]
            if not filename_parts or filename_parts == '':
                filename_parts = url.split('/')[-2] if len(url.split('/')) > 1 else f"page_{i}"
            
            filename = f"{i:03d}_{filename_parts}"
            
            # Generate description from URL
            description = generate_description_from_url(url)
            
            target = {
                "url": url,
                "filename": filename,
                "description": description,
                "prompt": intent_config[intent]["base_prompt"]
            }
            
            structure[intent]["targets"].append(target)
    
    return structure

def generate_description_from_url(url):
    """
    Generate description from URL path
    """
    path = url.split('/')[-1].replace('.html', '').replace('-', ' ')
    
    # Common translations
    translations = {
        'nganh': 'ngành',
        'tuyen': 'tuyển',
        'sinh': 'sinh',
        'phuong': 'phương',
        'thuc': 'thức',
        'xet': 'xét',
        'hoc': 'học',
        'phi': 'phí',
        'lien': 'liên',
        'he': 'hệ',
        'thong': 'thông',
        'tin': 'tin',
        'bao': 'báo',
        'chat': 'chất',
        'luong': 'lượng',
        'cao': 'cao',
        'tien': 'tiên',
        'dai': 'đại',
        'tra': 'trà'
    }
    
    # Apply translations
    for key, value in translations.items():
        path = path.replace(key, value)
    
    return path.title()

def main():
    """
    Main function to extract URLs and create crawl structure
    """
    md_file = "output/https_tuyensinh.ctu.edu.vn_.md"
    
    print("🔍 Extracting URLs from markdown file...")
    urls = extract_urls_from_markdown(md_file)
    print(f"📊 Found {len(urls)} unique URLs")
    
    print("\n📂 Categorizing URLs by intent...")
    categorized = categorize_urls_by_intent(urls)
    
    for intent, intent_urls in categorized.items():
        print(f"   {intent}: {len(intent_urls)} URLs")
    
    print("\n🏗️ Creating CRAWL_STRUCTURE...")
    crawl_structure = create_crawl_structure_from_urls(categorized)
    
    # Save to file
    output_file = "crawl_structure_from_urls.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(crawl_structure, f, indent=2, ensure_ascii=False)
    
    print(f"✅ CRAWL_STRUCTURE saved to: {output_file}")
    
    # Print summary
    print(f"\n📊 Summary:")
    total_targets = sum(len(intent_data['targets']) for intent_data in crawl_structure.values())
    print(f"   📂 Intents: {len(crawl_structure)}")
    print(f"   📄 Total targets: {total_targets}")
    
    # Show structure
    print(f"\n📁 Structure:")
    for intent, intent_data in crawl_structure.items():
        print(f"   📂 {intent}/ ({len(intent_data['targets'])} files)")
        for target in intent_data['targets']:
            print(f"      📄 {target['filename']}.json - {target['description']}")
    
    return crawl_structure

if __name__ == "__main__":
    main() 