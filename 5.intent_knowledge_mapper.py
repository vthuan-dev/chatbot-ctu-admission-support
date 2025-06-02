import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv


class IntentKnowledgeMapper:
    """Maps user intents to knowledge base queries and generates responses"""
    
    def __init__(self, intent_file: str, knowledge_file: str):
        """Initialize mapper with intent dataset and knowledge base"""
        
        # Load intent dataset
        with open(intent_file, 'r', encoding='utf-8') as f:
            self.intent_data = json.load(f)
        
        # Load knowledge base
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)
        
        # Define mapping rules
        self.mapping_rules = self._define_mapping_rules()
        
        # Response templates
        self.response_templates = self._define_response_templates()
    
    def _define_mapping_rules(self) -> Dict[str, Dict]:
        """Define how each intent maps to knowledge base queries"""
        
        return {
            "ask_program_fee": {
                "knowledge_source": "programs",
                "query_fields": ["tuition_fee"],
                "required_entities": ["program_name", "program_code"],
                "fallback_response": "Xin lỗi, tôi chưa có thông tin học phí cho ngành này. Bạn có thể liên hệ hotline 0292 3872 728 để biết thêm chi tiết."
            },
            
            "ask_program_duration": {
                "knowledge_source": "programs",
                "query_fields": ["duration"],
                "required_entities": ["program_name", "program_code"],
                "fallback_response": "Thời gian đào tạo chuẩn tại CTU thường là 4 năm cho hầu hết các ngành, riêng ngành Y khoa là 6 năm và Dược học là 5 năm."
            },
            
            "ask_admission_score": {
                "knowledge_source": "programs",
                "query_fields": ["admission_score_2024", "admission_score_2023"],
                "required_entities": ["program_name", "program_code", "year"],
                "fallback_response": "Điểm chuẩn các năm trước chỉ mang tính tham khảo. Điểm chuẩn 2025 sẽ được công bố sau khi có kết quả xét tuyển."
            },
            
            "ask_admission_method": {
                "knowledge_source": "admission_methods",
                "query_fields": ["method_name", "description", "requirements"],
                "required_entities": ["method_type"],
                "fallback_response": "CTU có 6 phương thức xét tuyển: Điểm thi THPT, Học bạ THPT, Kết quả V-SAT, Xét tuyển thẳng, Ưu tiên xét tuyển và phương thức Kết hợp."
            },
            
            "ask_program_info": {
                "knowledge_source": "programs",
                "query_fields": ["description", "career_opportunities", "skills"],
                "required_entities": ["program_name"],
                "fallback_response": "Bạn có thể tìm hiểu chi tiết về ngành học tại website tuyển sinh CTU hoặc liên hệ trực tiếp với khoa chuyên ngành."
            },
            
            "ask_scholarship": {
                "knowledge_source": "scholarships",
                "query_fields": ["scholarship_name", "value", "requirements"],
                "required_entities": ["scholarship_type"],
                "fallback_response": "CTU có nhiều loại học bổng: học bổng khuyến khích học tập, học bổng tài năng, học bổng vượt khó và học bổng từ doanh nghiệp."
            },
            
            "ask_dormitory": {
                "knowledge_source": "facilities",
                "query_fields": ["location", "capacity", "fee", "registration"],
                "required_entities": ["dormitory_info"],
                "fallback_response": "CTU có hệ thống ký túc xá với sức chứa hơn 3000 chỗ. Phí KTX từ 150.000-300.000đ/tháng tùy loại phòng."
            },
            
            "ask_enrollment_process": {
                "knowledge_source": "procedures",
                "query_fields": ["steps", "documents", "timeline"],
                "required_entities": ["process_type"],
                "fallback_response": "Thủ tục nhập học bao gồm: xác nhận nhập học online, nộp hồ sơ, đóng học phí và nhận thẻ sinh viên. Chi tiết sẽ được thông báo trong giấy báo trúng tuyển."
            },
            
            "ask_contact_info": {
                "knowledge_source": "contact_info",
                "query_fields": ["hotline", "email", "facebook", "address"],
                "required_entities": ["contact_type"],
                "fallback_response": "Liên hệ tư vấn tuyển sinh CTU: Hotline 0292 3872 728, Email: tuyensinh@ctu.edu.vn, Facebook: fb.com/ctu.tvts"
            },
            
            "ask_campus_location": {
                "knowledge_source": "facilities",
                "query_fields": ["address", "map_link", "transportation"],
                "required_entities": ["campus_name"],
                "fallback_response": "CTU có cơ sở chính tại Khu II, đường 3/2, Q. Ninh Kiều, TP. Cần Thơ và cơ sở Hòa An tại H. Phụng Hiệp, Hậu Giang."
            }
        }
    
    def _define_response_templates(self) -> Dict[str, List[str]]:
        """Define response templates for each intent"""
        
        return {
            "ask_program_fee": [
                "Học phí ngành {program_name} (mã {program_code}) là {tuition_fee}/năm.",
                "Ngành {program_name} có mức học phí {tuition_fee} mỗi năm học.",
                "Mã ngành {program_code} - {program_name} có học phí {tuition_fee}/năm."
            ],
            
            "ask_program_duration": [
                "Thời gian đào tạo ngành {program_name} là {duration}.",
                "Ngành {program_name} (mã {program_code}) học trong {duration}.",
                "Bạn sẽ học ngành {program_name} trong {duration} tại CTU."
            ],
            
            "ask_admission_score": [
                "Điểm chuẩn ngành {program_name} năm {year} là {admission_score} điểm.",
                "Năm {year}, ngành {program_name} (mã {program_code}) lấy điểm chuẩn {admission_score}.",
                "Điểm xét tuyển {program_name} năm {year}: {admission_score} điểm."
            ],
            
            "ask_admission_method": [
                "CTU xét tuyển bằng {method_name}. {description}",
                "Phương thức {method_name}: {description}. Yêu cầu: {requirements}",
                "Bạn có thể xét tuyển qua {method_name}. {description}"
            ],
            
            "ask_contact_info": [
                "Thông tin liên hệ CTU: {contact_details}",
                "Bạn có thể liên hệ qua: {contact_details}",
                "Liên hệ tư vấn: {contact_details}"
            ]
        }
    
    def query_knowledge(self, intent: str, entities: Dict[str, str]) -> Optional[Dict]:
        """Query knowledge base based on intent and entities"""
        
        if intent not in self.mapping_rules:
            return None
        
        rule = self.mapping_rules[intent]
        knowledge_source = rule["knowledge_source"]
        
        # Get data from knowledge base
        if knowledge_source not in self.knowledge_base.get("data", {}):
            return None
        
        data = self.knowledge_base["data"][knowledge_source]
        
        # For lists, search for matching item
        if isinstance(data, list):
            for item in data:
                # Check if item matches any entity
                match = False
                for entity_key, entity_value in entities.items():
                    if entity_key == "program_code" and item.get("program_code") == entity_value:
                        match = True
                        break
                    elif entity_key == "program_name" and entity_value.lower() in item.get("program_name", "").lower():
                        match = True
                        break
                
                if match:
                    return item
        
        # For dict, return directly
        elif isinstance(data, dict):
            return data
        
        return None
    
    def generate_response(self, intent: str, entities: Dict[str, str], knowledge: Optional[Dict] = None) -> str:
        """Generate response based on intent, entities and knowledge"""
        
        if intent not in self.mapping_rules:
            return "Xin lỗi, tôi chưa hiểu câu hỏi của bạn. Bạn có thể hỏi lại được không?"
        
        rule = self.mapping_rules[intent]
        
        # If no knowledge found, use fallback
        if not knowledge:
            return rule["fallback_response"]
        
        # Get template
        templates = self.response_templates.get(intent, [])
        if not templates:
            return rule["fallback_response"]
        
        # Select template (can be randomized)
        template = templates[0]
        
        # Fill template with knowledge and entities
        response_data = {**entities, **knowledge}
        
        try:
            response = template.format(**response_data)
        except KeyError:
            # If template formatting fails, use fallback
            response = rule["fallback_response"]
        
        return response
    
    def process_question(self, question: str, detected_intent: str, extracted_entities: Dict[str, str]) -> str:
        """Process a question and generate response"""
        
        # Query knowledge base
        knowledge = self.query_knowledge(detected_intent, extracted_entities)
        
        # Generate response
        response = self.generate_response(detected_intent, extracted_entities, knowledge)
        
        return response
    
    def validate_mapping(self) -> Dict[str, Any]:
        """Validate that all intents have proper mappings"""
        
        validation_report = {
            "timestamp": datetime.now().isoformat(),
            "total_intents": len(self.intent_data.get("intent_categories", [])),
            "mapped_intents": len(self.mapping_rules),
            "coverage": {},
            "issues": []
        }
        
        # Check each intent
        for category in self.intent_data.get("intent_categories", []):
            intent_id = category["intent_id"]
            
            if intent_id in self.mapping_rules:
                # Check if knowledge source exists
                rule = self.mapping_rules[intent_id]
                knowledge_source = rule["knowledge_source"]
                
                if knowledge_source in self.knowledge_base.get("data", {}):
                    data_count = len(self.knowledge_base["data"][knowledge_source]) \
                               if isinstance(self.knowledge_base["data"][knowledge_source], list) else 1
                    
                    validation_report["coverage"][intent_id] = {
                        "status": "mapped",
                        "knowledge_items": data_count
                    }
                else:
                    validation_report["coverage"][intent_id] = {
                        "status": "missing_knowledge",
                        "issue": f"Knowledge source '{knowledge_source}' not found"
                    }
                    validation_report["issues"].append(
                        f"Intent '{intent_id}' maps to non-existent knowledge source '{knowledge_source}'"
                    )
            else:
                validation_report["coverage"][intent_id] = {
                    "status": "unmapped",
                    "issue": "No mapping rule defined"
                }
                validation_report["issues"].append(f"Intent '{intent_id}' has no mapping rule")
        
        return validation_report
    
    def save_mapping_config(self, output_file: str = "output/intent_knowledge_mapping.json"):
        """Save mapping configuration to file"""
        
        mapping_config = {
            "version": "1.0",
            "created_date": datetime.now().isoformat(),
            "mapping_rules": self.mapping_rules,
            "response_templates": self.response_templates,
            "statistics": {
                "total_intents": len(self.mapping_rules),
                "total_templates": sum(len(templates) for templates in self.response_templates.values())
            }
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Mapping configuration saved to: {output_path}")


def test_mapper():
    """Test the intent-knowledge mapper with sample questions"""
    
    print("🧪 Testing Intent-Knowledge Mapper...")
    
    # Initialize mapper (using dummy files for testing)
    # In production, use actual files from previous steps
    mapper = IntentKnowledgeMapper(
        intent_file="output/intent_dataset/ctu_intent_questions.json",
        knowledge_file="output/knowledge_base/ctu_knowledge_base.json"
    )
    
    # Test cases
    test_cases = [
        {
            "question": "Học phí ngành CNTT là bao nhiêu?",
            "intent": "ask_program_fee",
            "entities": {"program_name": "Công nghệ thông tin", "program_code": "7480201"}
        },
        {
            "question": "CTU có KTX không?",
            "intent": "ask_dormitory",
            "entities": {"dormitory_info": "ký túc xá"}
        },
        {
            "question": "Làm sao để liên hệ tư vấn?",
            "intent": "ask_contact_info",
            "entities": {"contact_type": "general"}
        }
    ]
    
    print("\n📝 Test Results:")
    for i, test in enumerate(test_cases, 1):
        response = mapper.process_question(
            test["question"],
            test["intent"],
            test["entities"]
        )
        print(f"\n{i}. Q: {test['question']}")
        print(f"   A: {response}")
    
    # Validate mapping
    print("\n🔍 Validation Report:")
    validation = mapper.validate_mapping()
    print(f"   - Total intents: {validation['total_intents']}")
    print(f"   - Mapped intents: {validation['mapped_intents']}")
    print(f"   - Issues found: {len(validation['issues'])}")
    
    if validation['issues']:
        print("\n⚠️  Issues:")
        for issue in validation['issues'][:5]:
            print(f"   - {issue}")
    
    # Save mapping configuration
    mapper.save_mapping_config()


def main():
    """Main function"""
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Test the mapper
    test_mapper()
    
    print("\n🎉 Intent-Knowledge mapping completed!")


if __name__ == "__main__":
    main() 