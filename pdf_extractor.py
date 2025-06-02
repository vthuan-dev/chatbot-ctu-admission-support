import asyncio
import json
import os
import requests
from pathlib import Path
import openai
from dotenv import load_dotenv

# PDF processing libraries
try:
    import PyPDF2
    import fitz  # PyMuPDF
    import pdfplumber
    PDF_LIBS_AVAILABLE = True
except ImportError:
    PDF_LIBS_AVAILABLE = False
    print("⚠️  PDF libraries not installed. Run: pip install PyPDF2 PyMuPDF pdfplumber")

def extract_with_pypdf2(pdf_path):
    """Extract text using PyPDF2 (basic)"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                text += f"\n--- Page {page_num} ---\n{page_text}\n"
            return text
    except Exception as e:
        print(f"❌ PyPDF2 error: {e}")
        return None

def extract_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF (better formatting)"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        tables = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text()
            text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            # Try to extract tables
            try:
                page_tables = page.find_tables()
                for table in page_tables:
                    table_data = table.extract()
                    tables.append({
                        'page': page_num + 1,
                        'data': table_data
                    })
            except:
                pass
        
        doc.close()
        return {'text': text, 'tables': tables}
    except Exception as e:
        print(f"❌ PyMuPDF error: {e}")
        return None

def extract_with_pdfplumber(pdf_path):
    """Extract text and tables using pdfplumber (best for tables)"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num} ---\n{page_text}\n"
                
                # Extract tables
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        tables.append({
                            'page': page_num,
                            'data': table
                        })
            
            return {'text': text, 'tables': tables}
    except Exception as e:
        print(f"❌ pdfplumber error: {e}")
        return None

def download_pdf_from_url(url, save_path):
    """Download PDF from URL"""
    try:
        print(f"📥 Downloading PDF from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {save_path}")
        return True
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

def extract_from_pdf(pdf_path):
    """Extract content using multiple methods for best results"""
    if not PDF_LIBS_AVAILABLE:
        print("❌ PDF libraries not available")
        return None
    
    print(f"📄 Processing PDF: {pdf_path}")
    
    # Try different extraction methods
    results = {}
    
    # Method 1: pdfplumber (best for tables)
    print("🔧 Trying pdfplumber...")
    plumber_result = extract_with_pdfplumber(pdf_path)
    if plumber_result:
        results['pdfplumber'] = plumber_result
        print(f"  ✅ pdfplumber: {len(plumber_result['text'])} chars, {len(plumber_result['tables'])} tables")
    
    # Method 2: PyMuPDF (good balance)
    print("🔧 Trying PyMuPDF...")
    pymupdf_result = extract_with_pymupdf(pdf_path)
    if pymupdf_result:
        results['pymupdf'] = pymupdf_result
        print(f"  ✅ PyMuPDF: {len(pymupdf_result['text'])} chars, {len(pymupdf_result.get('tables', []))} tables")
    
    # Method 3: PyPDF2 (fallback)
    print("🔧 Trying PyPDF2...")
    pypdf2_result = extract_with_pypdf2(pdf_path)
    if pypdf2_result:
        results['pypdf2'] = {'text': pypdf2_result, 'tables': []}
        print(f"  ✅ PyPDF2: {len(pypdf2_result)} chars")
    
    # Choose best result
    if 'pdfplumber' in results:
        best_result = results['pdfplumber']
        method = 'pdfplumber'
    elif 'pymupdf' in results:
        best_result = results['pymupdf']
        method = 'pymupdf'
    elif 'pypdf2' in results:
        best_result = results['pypdf2']
        method = 'pypdf2'
    else:
        print("❌ All extraction methods failed")
        return None
    
    print(f"🎯 Using best result from: {method}")
    return best_result

def convert_pdf_to_markdown(pdf_content):
    """Convert PDF content to markdown format"""
    if not pdf_content:
        return ""
    
    markdown = "# PDF Document Content\n\n"
    
    # Add main text
    markdown += "## Document Text\n\n"
    markdown += pdf_content['text']
    
    # Add tables
    if pdf_content.get('tables'):
        markdown += "\n\n## Tables\n\n"
        for i, table_info in enumerate(pdf_content['tables'], 1):
            markdown += f"### Table {i} (Page {table_info['page']})\n\n"
            
            table_data = table_info['data']
            if table_data and len(table_data) > 0:
                # Create markdown table
                if table_data[0]:  # Header row
                    header = " | ".join([str(cell) if cell else "" for cell in table_data[0]])
                    separator = " | ".join(["---"] * len(table_data[0]))
                    
                    markdown += f"| {header} |\n"
                    markdown += f"| {separator} |\n"
                    
                    # Data rows
                    for row in table_data[1:]:
                        if row:
                            row_text = " | ".join([str(cell) if cell else "" for cell in row])
                            markdown += f"| {row_text} |\n"
                
                markdown += "\n"
    
    return markdown

async def extract_qa_from_pdf_content(markdown_content, api_key, pdf_name):
    """Extract Q&A from PDF content using LLM"""
    print("🤖 Extracting Q&A from PDF content...")
    
    client = openai.AsyncOpenAI(api_key=api_key)
    
    prompt = f"""
    Bạn là chuyên gia tạo chatbot tư vấn tuyển sinh CTU.
    Từ nội dung file PDF "{pdf_name}" được cung cấp, hãy tạo các câu hỏi-trả lời CỤ THỂ.
    
    YÊU CẦU:
    - Tạo 25-35 câu hỏi từ nội dung PDF
    - Câu trả lời phải chính xác dựa trên dữ liệu có sẵn
    - Không bịa đặt thông tin
    - Tập trung vào: ngành học, tuyển sinh, học phí, chương trình đào tạo, quy chế
    - Nếu có bảng số liệu, tạo câu hỏi về các con số cụ thể
    
    Trả về JSON format:
    {{
      "intent": "tuyen_sinh_ctu_pdf",
      "description": "Q&A từ file PDF CTU: {pdf_name}",
      "count": 30,
      "qa_pairs": [
        {{
          "id": "qa_001",
          "question": "Câu hỏi cụ thể từ PDF",
          "answer": "Câu trả lời chi tiết dựa trên nội dung PDF",
          "category": "nganh_hoc/tuyen_sinh/hoc_phi/quy_che/...",
          "confidence": 0.9,
          "source_type": "pdf_document",
          "source_file": "{pdf_name}"
        }}
      ]
    }}
    """
    
    try:
        # Split content if too long
        max_content_length = 15000
        if len(markdown_content) > max_content_length:
            markdown_content = markdown_content[:max_content_length] + "\n\n[Content truncated for processing]"
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Nội dung file PDF:\n\n{markdown_content}"}
            ],
            temperature=0.0,
            max_tokens=8000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ Error in LLM extraction: {e}")
        return None

async def process_pdf_file(pdf_path):
    """Complete pipeline: PDF → Text → Markdown → Q&A"""
    print("🚀 PROCESSING PDF FILE FOR CTU CHATBOT\n")
    
    # Extract content from PDF
    pdf_content = extract_from_pdf(pdf_path)
    if not pdf_content:
        return
    
    # Convert to markdown
    markdown_content = convert_pdf_to_markdown(pdf_content)
    
    # Save markdown for reference
    os.makedirs("output", exist_ok=True)
    markdown_file = "output/pdf_extracted.md"
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"💾 Markdown saved: {markdown_file}")
    
    # Extract Q&A using LLM
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return
    
    pdf_name = Path(pdf_path).name
    qa_content = await extract_qa_from_pdf_content(markdown_content, api_key, pdf_name)
    
    if qa_content:
        # Save Q&A JSON
        try:
            # Clean JSON response
            content = qa_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            qa_data = json.loads(content)
            
            qa_file = "output/pdf_qa_extracted.json"
            with open(qa_file, "w", encoding="utf-8") as f:
                json.dump(qa_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ SUCCESS!")
            print(f"📄 PDF processed: {pdf_path}")
            print(f"📝 Markdown: {markdown_file}")
            print(f"🤖 Q&A JSON: {qa_file}")
            print(f"❓ Generated {qa_data.get('count', 0)} Q&A pairs")
            print(f"📊 Tables found: {len(pdf_content.get('tables', []))}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            raw_file = "output/pdf_qa_raw.txt"
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(qa_content)
            print(f"💾 Raw response saved: {raw_file}")

async def process_pdf_from_url(url):
    """Download and process PDF from URL"""
    temp_pdf = "temp_downloaded.pdf"
    
    if download_pdf_from_url(url, temp_pdf):
        await process_pdf_file(temp_pdf)
        # Clean up
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)
    else:
        print("❌ Failed to download PDF")

def main():
    load_dotenv()
    
    if not PDF_LIBS_AVAILABLE:
        print("❌ Please install PDF libraries:")
        print("   pip install PyPDF2 PyMuPDF pdfplumber")
        return
    
    print("📑 PDF EXTRACTOR FOR CTU CHATBOT")
    print("1. Process local PDF file")
    print("2. Download and process PDF from URL")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        # Find PDF files in current directory
        pdf_files = list(Path(".").glob("*.pdf"))
        
        if pdf_files:
            print("\n📄 Found PDF files:")
            for i, file in enumerate(pdf_files, 1):
                print(f"  {i}. {file.name}")
            
            try:
                file_choice = int(input(f"\nSelect file (1-{len(pdf_files)}): ")) - 1
                selected_file = pdf_files[file_choice]
                asyncio.run(process_pdf_file(selected_file))
            except (ValueError, IndexError):
                print("❌ Invalid selection")
        else:
            print("❌ No .pdf files found in current directory")
            print("💡 Usage: Place your PDF file in the project folder and run again")
    
    elif choice == "2":
        url = input("Enter PDF URL: ").strip()
        if url:
            asyncio.run(process_pdf_from_url(url))
        else:
            print("❌ No URL provided")
    
    else:
        print("❌ Invalid option")

if __name__ == "__main__":
    main() 