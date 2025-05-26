import json
import os
from pathlib import Path
from datetime import datetime

def load_qa_from_json(json_file):
    """
    Load Q&A pairs from extraction JSON file
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        qa_pairs = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            for chunk in data:
                if isinstance(chunk, dict) and 'qa_pairs' in chunk:
                    qa_pairs.extend(chunk['qa_pairs'])
        elif isinstance(data, dict) and 'qa_pairs' in data:
            qa_pairs.extend(data['qa_pairs'])
        
        return qa_pairs
    except Exception as e:
        print(f"⚠️ Error loading {json_file}: {e}")
        return []

def create_final_dataset():
    """
    Create final chatbot dataset from all extraction files
    """
    print("🚀 Creating final chatbot dataset...")
    
    # Find all extraction JSON files
    output_dir = Path("output")
    extraction_files = [
        "output/https_tuyensinh.ctu.edu.vn_.json",
        "output/ctu_detailed_majors_extracted.json"
    ]
    
    # Add any other extracted files
    for file in output_dir.glob("*_extracted.json"):
        if str(file) not in extraction_files:
            extraction_files.append(str(file))
    
    print(f"📁 Found {len(extraction_files)} extraction files:")
    for file in extraction_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (not found)")
    
    # Collect all Q&A pairs
    all_qa_pairs = []
    file_stats = {}
    
    for file_path in extraction_files:
        if not Path(file_path).exists():
            continue
            
        qa_pairs = load_qa_from_json(file_path)
        file_stats[file_path] = len(qa_pairs)
        all_qa_pairs.extend(qa_pairs)
        print(f"📝 {Path(file_path).name}: {len(qa_pairs)} Q&A pairs")
    
    # Remove duplicates based on question
    unique_qa_pairs = []
    seen_questions = set()
    
    for qa in all_qa_pairs:
        question = qa.get('question', '').strip().lower()
        if question and question not in seen_questions:
            seen_questions.add(question)
            unique_qa_pairs.append(qa)
    
    print(f"\n📊 Dataset Statistics:")
    print(f"   📝 Total Q&A pairs: {len(all_qa_pairs)}")
    print(f"   🔄 Unique Q&A pairs: {len(unique_qa_pairs)}")
    print(f"   ❌ Duplicates removed: {len(all_qa_pairs) - len(unique_qa_pairs)}")
    
    # Categorize Q&A pairs
    categories = {}
    priorities = {1: 0, 2: 0, 3: 0}
    
    for qa in unique_qa_pairs:
        category = qa.get('category', 'unknown')
        priority = qa.get('priority', 3)
        
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
        
        if priority in priorities:
            priorities[priority] += 1
    
    print(f"\n📂 Categories:")
    for category, count in sorted(categories.items()):
        print(f"   📁 {category}: {count} pairs")
    
    print(f"\n⭐ Priorities:")
    for priority, count in priorities.items():
        print(f"   {priority}⭐: {count} pairs")
    
    # Create final dataset
    final_dataset = {
        "metadata": {
            "created_date": datetime.now().isoformat(),
            "source": "CTU Admission Website Extraction",
            "total_qa_pairs": len(unique_qa_pairs),
            "categories": list(categories.keys()),
            "source_files": file_stats,
            "description": "Vietnamese Q&A dataset for CTU admission counseling chatbot"
        },
        "qa_pairs": unique_qa_pairs,
        "categories": categories,
        "priorities": priorities
    }
    
    # Save final dataset
    final_file = "output/ctu_chatbot_dataset_final.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Final dataset saved: {final_file}")
    
    # Create training format (simple Q&A pairs)
    training_data = []
    for qa in unique_qa_pairs:
        training_data.append({
            "question": qa.get('question', ''),
            "answer": qa.get('answer', ''),
            "category": qa.get('category', 'general'),
            "priority": qa.get('priority', 3)
        })
    
    training_file = "output/ctu_chatbot_training_data.json"
    with open(training_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Training data saved: {training_file}")
    
    # Show sample Q&A
    print(f"\n📝 Sample Q&A pairs (first 5):")
    for i, qa in enumerate(unique_qa_pairs[:5], 1):
        print(f"   {i}. Q: {qa.get('question', 'N/A')}")
        print(f"      A: {qa.get('answer', 'N/A')[:80]}...")
        print(f"      Category: {qa.get('category', 'N/A')}, Priority: {qa.get('priority', 'N/A')}")
        print()
    
    print(f"🎉 Dataset creation completed!")
    print(f"💡 You can now use these files to train your chatbot:")
    print(f"   📄 Full dataset: {final_file}")
    print(f"   📄 Training data: {training_file}")

if __name__ == "__main__":
    create_final_dataset() 