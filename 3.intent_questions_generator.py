import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import re
from difflib import SequenceMatcher

import openai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential


class IntentQuestion(BaseModel):
    """Model for a single intent question"""
    text: str
    entities: List[str] = Field(default_factory=list)
    is_template: bool = False
    source: str = "generated"
    confidence: float = 0.9


class IntentCategory(BaseModel):
    """Model for an intent category"""
    intent_id: str
    intent_name: str
    description: str
    entities_required: List[str]
    keywords: List[str]
    questions: List[IntentQuestion]
    examples_needed: int = 50  # Target number of questions per intent


class IntentDataset(BaseModel):
    """Model for the complete intent dataset"""
    metadata: Dict[str, Any]
    intent_categories: List[IntentCategory]
    total_questions: int = 0


# Define style patterns for question variations
style_patterns = {
    "formal": [
        "Xin cho biết", "Vui lòng cho biết", "Kính mong quý thầy/cô cho biết",
        "Tôi muốn hỏi", "Tôi xin phép được hỏi", "Tôi thắc mắc",
        "Xin được hỏi", "Cho phép tôi hỏi", "Tôi có thắc mắc",
        "Mong được giải đáp", "Xin được tư vấn", "Tôi muốn tìm hiểu",
        "Cho tôi hỏi thông tin về", "Xin được tư vấn về", "Mong được hướng dẫn về",
        "Tôi đang quan tâm đến", "Tôi muốn được tư vấn về", "Xin hỏi thông tin chi tiết về"
    ],
    "informal": [
        "Cho mình hỏi", "Cho em hỏi", "Cho tôi hỏi",
        "Mình muốn biết", "Em muốn hỏi", "Tôi muốn hỏi",
        "Chị ơi cho em hỏi", "Anh ơi cho em hỏi", "Thầy cô ơi cho em hỏi",
        "Mình đang quan tâm", "Em đang tìm hiểu", "Cho mình tham khảo",
        "Em muốn được tư vấn", "Mình cần tư vấn", "Cho em xin thông tin",
        "Em đang phân vân", "Mình đang cân nhắc", "Em muốn được giải đáp thắc mắc"
    ],
    "teen": [
        "cho e hỏi", "cho mk hỏi", "cho t hỏi",
        "e muốn biết", "mk muốn hỏi", "t muốn hỏi",
        "chị ơi cho e hỏi xíu", "anh ơi cho e hỏi tí", "thầy cô ơi cho e hỏi tí",
        "e đang tìm hiểu", "mk đang tìm hiểu", "cho e tham khảo tí",
        "e đang phân vân quá", "mk cần tư vấn tí", "cho e hóng tí info",
        "cho e xin ít thông tin", "e đang băn khoăn quá", "cho mk tham khảo tí"
    ],
    "typo": [
        "cho e hoi", "cho mk hoi", "cho t hoi",
        "e muon biet", "mk muon hoi", "t muon hoi",
        "chi oi cho e hoi xiu", "a oi cho e hoi ti", "thay co oi cho e hoi ti",
        "e dang tim hieu", "mk dang tim hieu", "cho e tham khao ti",
        "e dang phan van qua", "mk can tu van ti", "cho e hong ti info",
        "cho e xin it thong tin", "e dang ban khoan qua", "cho mk tham khao ti"
    ],
    "question_types": [
        "có thể cho biết", "làm ơn cho biết", "giúp mình",
        "cho mình/em biết", "mình/em cần biết", "mình/em muốn biết",
        "ai biết", "có ai biết", "có ai rõ",
        "làm sao", "như thế nào", "ra sao",
        "bao nhiêu", "khi nào", "ở đâu",
        "có được không", "có khó không", "có phải không",
        "thế nào ạ", "thế nào nhỉ", "vậy ạ"
    ],
    "emotions": [
        "rất quan tâm về", "đang băn khoăn về", "đang thắc mắc về",
        "rất muốn biết về", "rất cần biết về", "rất mong biết về",
        "lo lắng về", "không rõ về", "chưa hiểu về",
        "đang phân vân về", "đang cân nhắc về", "đang do dự về",
        "rất hứng thú với", "rất thích", "rất muốn học",
        "đang mong muốn được", "đang hy vọng được", "đang mơ ước được"
    ],
    "specific": [
        "cho hỏi cụ thể về", "xin thông tin chi tiết về", "cần tư vấn kỹ về",
        "muốn biết rõ hơn về", "cần được tư vấn kỹ càng về", "xin được giải thích rõ về",
        "mong được tư vấn cụ thể về", "cần thông tin chi tiết về", "muốn hiểu rõ hơn về"
    ]
}

# Define additional question patterns
additional_patterns = {
    "ask_program_fee": [
        "Chi phí một năm học {program_name} khoảng bao nhiêu?",
        "Học phí {program_name} có đắt không?",
        "Ngoài học phí, {program_name} còn phí gì không?",
        "Có được giảm học phí {program_name} không?",
        "Học phí {program_name} trả theo kỳ hay năm?",
        "So với các trường khác thì học phí {program_name} thế nào?",
        "Học phí ngành {program_name} năm nay có tăng không?",
        "Mức học phí cụ thể của ngành {program_name} là bao nhiêu?",
        "Có chính sách hỗ trợ học phí cho ngành {program_name} không?",
        "Học phí ngành {program_name} có đóng theo tín chỉ không?",
        "Chi phí ước tính cho toàn khóa học {program_name}?",
        "Có được trả góp học phí ngành {program_name} không?"
    ],
    "ask_program_duration": [
        "Thời gian học {program_name} có rút ngắn được không?",
        "Học {program_name} có được học nhanh hơn không?",
        "Học {program_name} mấy học kỳ thì xong?",
        "Có thể kéo dài thời gian học {program_name} không?",
        "Học {program_name} có học kỳ hè không?",
        "Thời gian thực tập {program_name} là bao lâu?",
        "Ngành {program_name} học mấy năm thì ra trường?",
        "Có thể học vượt ngành {program_name} không?",
        "Thời gian tối đa được phép học ngành {program_name}?",
        "Học {program_name} có được bảo lưu không?",
        "Ngành {program_name} có được học song song không?",
        "Lịch học ngành {program_name} như thế nào?"
    ],
    "ask_admission_score": [
        "Điểm chuẩn {program_name} năm nay dự kiến thế nào?",
        "Điểm xét tuyển {program_name} có tăng không?",
        "Điểm sàn {program_name} là bao nhiêu?",
        "Điểm học bạ {program_name} lấy như thế nào?",
        "Điểm xét tuyển thẳng {program_name} thế nào?",
        "So với năm trước điểm {program_name} có khác không?",
        "Điểm chuẩn {program_name} năm {year} là bao nhiêu?",
        "Điểm trúng tuyển {program_name} các năm trước?",
        "Tỉ lệ chọi ngành {program_name} năm nay?",
        "Điểm xét tuyển học bạ {program_name} lấy những môn nào?",
        "Điểm ưu tiên khu vực cho ngành {program_name}?",
        "Điểm xét tuyển {program_name} theo phương thức {method_type}?"
    ],
    "ask_program_info": [
        "Sinh viên {program_name} được học những môn gì?",
        "Sau khi tốt nghiệp {program_name} làm việc ở đâu?",
        "Ngành {program_name} có nhiều việc làm không?",
        "Mức lương của sinh viên {program_name} ra trường?",
        "Có nên học ngành {program_name} không?",
        "Ngành {program_name} có phù hợp với nữ không?",
        "Chương trình đào tạo ngành {program_name} như thế nào?",
        "Cơ hội việc làm ngành {program_name} ra sao?",
        "Ngành {program_name} có thực tập không?",
        "Điểm mạnh của ngành {program_name} CTU?",
        "Ngành {program_name} có liên kết doanh nghiệp không?",
        "Triển vọng nghề nghiệp ngành {program_name} thế nào?"
    ],
    "ask_scholarship": [
        "Học bổng {scholarship_type} có giá trị bao nhiêu?",
        "Điều kiện nhận học bổng {scholarship_type}?",
        "Thời gian xét học bổng {scholarship_type}?",
        "Có được nhận nhiều loại học bổng cùng lúc không?",
        "Học bổng {scholarship_type} có duy trì được không?",
        "Quy trình đăng ký học bổng {scholarship_type}?",
        "Số lượng suất học bổng {scholarship_type}?",
        "Học bổng cho sinh viên ngành {program_name}?",
        "Các loại học bổng dành cho tân sinh viên?",
        "Học bổng khuyến khích học tập là gì?",
        "Điểm trung bình để được học bổng là bao nhiêu?",
        "Có học bổng cho sinh viên nghèo vượt khó không?"
    ],
    "ask_dormitory": [
        "Ký túc xá có wifi không?",
        "Giá phòng {dormitory_info} là bao nhiêu?",
        "Điều kiện để ở {dormitory_info}?",
        "Thời gian đăng ký {dormitory_info}?",
        "Có được nấu ăn trong {dormitory_info} không?",
        "Quy định sinh hoạt ở {dormitory_info}?",
        "Tiện ích trong {dormitory_info} có những gì?",
        "Có phòng máy lạnh trong {dormitory_info} không?",
        "Thủ tục đăng ký ở {dormitory_info}?",
        "An ninh ở {dormitory_info} thế nào?",
        "Có giới hạn giờ giấc ra vào không?",
        "Có được để xe trong {dormitory_info} không?"
    ],
    "ask_contact_info": [
        "Số điện thoại phòng đào tạo CTU?",
        "Email tư vấn tuyển sinh là gì?",
        "Địa chỉ văn phòng tuyển sinh ở đâu?",
        "Fanpage tuyển sinh CTU?",
        "Zalo tư vấn tuyển sinh?",
        "Thời gian làm việc phòng tuyển sinh?",
        "Có tư vấn trực tuyến không?",
        "Hotline tư vấn ngành {program_name}?",
        "Cách liên hệ với cố vấn học tập?",
        "Website tuyển sinh chính thức?",
        "Địa chỉ nộp hồ sơ trực tiếp?",
        "Kênh tư vấn tuyển sinh online?"
    ],
    "ask_campus_location": [
        "Địa chỉ {campus_name} ở đâu?",
        "Cách đi đến {campus_name}?",
        "Khoảng cách từ bến xe đến {campus_name}?",
        "Có xe buýt đến {campus_name} không?",
        "Bản đồ đường đi {campus_name}?",
        "Phương tiện di chuyển đến {campus_name}?",
        "Có ký túc xá gần {campus_name} không?",
        "Khoảng cách giữa các campus?",
        "Môi trường học tập ở {campus_name}?",
        "Cơ sở vật chất {campus_name} thế nào?",
        "Có căng tin ở {campus_name} không?",
        "Bãi giữ xe ở {campus_name}?"
    ]
}

# Define CTU-specific intent categories with enhanced diversity
CTU_INTENT_CATEGORIES = [
    {
        "intent_id": "ask_program_fee",
        "intent_name": "Hỏi học phí ngành học",
        "description": "Câu hỏi về học phí, chi phí đào tạo của các ngành",
        "entities_required": ["program_name", "program_code"],
        "keywords": ["học phí", "chi phí", "tiền học", "mức phí", "phí", "bao nhiêu tiền", "đóng học phí", "học phí mỗi kỳ", "học phí mỗi năm"],
        "seed_patterns": [
            "Học phí ngành {program_name} là bao nhiêu?",
            "Mã ngành {program_code} học phí bao nhiêu?",
            "Chi phí học ngành {program_name} CTU?",
            "Học phí mỗi kỳ của ngành {program_name} là bao nhiêu?",
            "Ngành {program_name} đóng học phí như thế nào?",
            "Học phí ngành {program_name} có tăng theo năm không?",
            "Có được miễn giảm học phí ngành {program_name} không?",
            "Học phí ngành {program_name} có khác với các trường khác không?"
        ]
    },
    {
        "intent_id": "ask_program_duration",
        "intent_name": "Hỏi thời gian đào tạo",
        "description": "Câu hỏi về thời gian học, số năm đào tạo",
        "entities_required": ["program_name", "program_code"],
        "keywords": ["thời gian", "bao lâu", "mấy năm", "học mấy năm", "thời gian đào tạo", "kỳ học", "học kỳ", "tín chỉ"],
        "seed_patterns": [
            "Ngành {program_name} học mấy năm?",
            "Thời gian đào tạo ngành {program_name} là bao lâu?",
            "Mã {program_code} học trong bao nhiêu năm?",
            "Ngành {program_name} có bao nhiêu tín chỉ?",
            "Có thể học nhanh hơn ngành {program_name} không?",
            "Ngành {program_name} có học kỳ hè không?",
            "Thời gian thực tập ngành {program_name} là bao lâu?",
            "Có được học vượt ngành {program_name} không?"
        ]
    },
    {
        "intent_id": "ask_admission_score",
        "intent_name": "Hỏi điểm chuẩn",
        "description": "Câu hỏi về điểm chuẩn, điểm xét tuyển các năm",
        "entities_required": ["program_name", "program_code", "year"],
        "keywords": ["điểm chuẩn", "điểm xét tuyển", "bao nhiêu điểm", "điểm đầu vào", "điểm trúng tuyển", "điểm sàn", "điểm liệt"],
        "seed_patterns": [
            "Điểm chuẩn ngành {program_name} năm {year} là bao nhiêu?",
            "Năm ngoái ngành {program_name} lấy bao nhiêu điểm?",
            "Điểm xét tuyển mã {program_code} CTU?",
            "Điểm sàn ngành {program_name} năm {year}?",
            "Điểm liệt ngành {program_name} là bao nhiêu?",
            "Điểm chuẩn ngành {program_name} có tăng không?",
            "Điểm xét tuyển học bạ ngành {program_name}?",
            "Điểm chuẩn ngành {program_name} theo từng phương thức?"
        ]
    },
    {
        "intent_id": "ask_admission_method",
        "intent_name": "Hỏi phương thức xét tuyển",
        "description": "Câu hỏi về các phương thức xét tuyển, cách thức đăng ký",
        "entities_required": ["program_name", "method_type"],
        "keywords": ["phương thức", "xét tuyển", "cách xét", "hình thức", "xét học bạ", "xét điểm thi", "đăng ký", "hồ sơ"],
        "seed_patterns": [
            "Ngành {program_name} xét tuyển bằng cách nào?",
            "Có thể xét học bạ vào ngành {program_name} không?",
            "CTU có những phương thức xét tuyển nào?",
            "Điều kiện xét tuyển ngành {program_name}?",
            "Hồ sơ xét tuyển ngành {program_name} cần những gì?",
            "Thời gian đăng ký xét tuyển ngành {program_name}?",
            "Có thể đăng ký nhiều phương thức ngành {program_name} không?",
            "Xét tuyển thẳng ngành {program_name} cần điều kiện gì?"
        ]
    },
    {
        "intent_id": "ask_program_info",
        "intent_name": "Hỏi thông tin ngành học",
        "description": "Câu hỏi chung về ngành học, cơ hội việc làm",
        "entities_required": ["program_name"],
        "keywords": ["ngành", "học gì", "ra trường", "làm gì", "cơ hội", "nghề nghiệp", "chương trình", "môn học"],
        "seed_patterns": [
            "Ngành {program_name} học những gì?",
            "Ra trường ngành {program_name} làm việc ở đâu?",
            "Giới thiệu về ngành {program_name} CTU?",
            "Chương trình đào tạo ngành {program_name} như thế nào?",
            "Cơ hội việc làm ngành {program_name} ra sao?",
            "Ngành {program_name} có thực tập không?",
            "Điểm mạnh của ngành {program_name} CTU?",
            "Ngành {program_name} có liên kết doanh nghiệp không?"
        ]
    },
    {
        "intent_id": "ask_scholarship",
        "intent_name": "Hỏi học bổng",
        "description": "Câu hỏi về các loại học bổng, điều kiện nhận học bổng",
        "entities_required": ["scholarship_type", "program_name"],
        "keywords": ["học bổng", "hỗ trợ", "miễn giảm", "tài trợ", "học phí", "sinh viên", "điều kiện", "thủ tục"],
        "seed_patterns": [
            "CTU có những loại học bổng nào?",
            "Điều kiện nhận học bổng ngành {program_name}?",
            "Làm sao để được học bổng tại CTU?",
            "Học bổng {scholarship_type} dành cho ngành {program_name}?",
            "Thủ tục xin học bổng ngành {program_name}?",
            "Học bổng có được cấp lại không?",
            "Học bổng ngành {program_name} có khó không?",
            "Có học bổng cho sinh viên mới ngành {program_name} không?"
        ]
    },
    {
        "intent_id": "ask_dormitory",
        "intent_name": "Hỏi ký túc xá",
        "description": "Câu hỏi về ký túc xá, chỗ ở cho sinh viên",
        "entities_required": ["dormitory_info"],
        "keywords": ["ký túc xá", "KTX", "chỗ ở", "phòng ở", "nội trú", "phòng trọ", "giá phòng", "tiện nghi"],
        "seed_patterns": [
            "CTU có ký túc xá không?",
            "Phí ký túc xá CTU bao nhiêu?",
            "Đăng ký KTX CTU như thế nào?",
            "Tiện nghi {dormitory_info} có gì?",
            "Giá phòng {dormitory_info} là bao nhiêu?",
            "Có phòng cho sinh viên nữ không?",
            "KTX có wifi không?",
            "Có được nấu ăn trong KTX không?"
        ]
    },
    {
        "intent_id": "ask_enrollment_process",
        "intent_name": "Hỏi quy trình nhập học",
        "description": "Câu hỏi về thủ tục nhập học, hồ sơ cần thiết",
        "entities_required": ["process_type"],
        "keywords": ["nhập học", "thủ tục", "hồ sơ", "đăng ký", "nộp hồ sơ", "giấy tờ", "thời gian", "địa điểm"],
        "seed_patterns": [
            "Thủ tục nhập học CTU như thế nào?",
            "Cần chuẩn bị hồ sơ gì để nhập học?",
            "Khi nào nhập học tại CTU?",
            "Địa điểm nộp hồ sơ nhập học?",
            "Có cần giấy khám sức khỏe không?",
            "Thời gian làm thủ tục nhập học?",
            "Có được hoãn nhập học không?",
            "Hồ sơ nhập học có cần công chứng không?"
        ]
    },
    {
        "intent_id": "ask_contact_info",
        "intent_name": "Hỏi thông tin liên hệ",
        "description": "Câu hỏi về cách liên hệ, tư vấn tuyển sinh",
        "entities_required": ["contact_type"],
        "keywords": ["liên hệ", "tư vấn", "số điện thoại", "email", "facebook", "địa chỉ", "hotline", "zalo"],
        "seed_patterns": [
            "Số điện thoại tư vấn tuyển sinh CTU?",
            "Làm sao để liên hệ tư vấn CTU?",
            "Facebook tuyển sinh CTU là gì?",
            "Email liên hệ phòng đào tạo?",
            "Hotline tư vấn tuyển sinh?",
            "Zalo tư vấn tuyển sinh CTU?",
            "Giờ làm việc phòng tuyển sinh?",
            "Địa chỉ liên hệ trực tiếp?"
        ]
    },
    {
        "intent_id": "ask_campus_location",
        "intent_name": "Hỏi vị trí cơ sở",
        "description": "Câu hỏi về địa điểm, cơ sở học tập",
        "entities_required": ["campus_name"],
        "keywords": ["địa chỉ", "ở đâu", "cơ sở", "khu", "campus", "đường", "phường", "quận"],
        "seed_patterns": [
            "CTU có những cơ sở nào?",
            "Địa chỉ CTU ở đâu?",
            "Khu {campus_name} CTU ở đâu?",
            "Đường đi đến {campus_name}?",
            "Có xe bus đến {campus_name} không?",
            "Khoảng cách giữa các cơ sở?",
            "Bãi đậu xe ở {campus_name}?",
            "Cơ sở vật chất {campus_name} như thế nào?"
        ]
    },
    {
        "intent_id": "ask_transfer_program",
        "intent_name": "Hỏi chuyển ngành",
        "description": "Câu hỏi về điều kiện và thủ tục chuyển ngành",
        "entities_required": ["program_name"],
        "keywords": ["chuyển ngành", "chuyển trường", "điều kiện", "thủ tục", "học lực", "điểm", "thời gian"],
        "seed_patterns": [
            "Điều kiện chuyển ngành {program_name}?",
            "Có được chuyển ngành {program_name} không?",
            "Thủ tục chuyển ngành như thế nào?",
            "Điểm trung bình để chuyển ngành {program_name}?",
            "Thời gian được phép chuyển ngành?",
            "Chuyển ngành có phải thi lại không?",
            "Học phí khi chuyển ngành {program_name}?",
            "Có được chuyển ngành nhiều lần không?"
        ]
    },
    {
        "intent_id": "ask_credit_transfer",
        "intent_name": "Hỏi chuyển tín chỉ",
        "description": "Câu hỏi về việc chuyển đổi, công nhận tín chỉ",
        "entities_required": ["program_name"],
        "keywords": ["tín chỉ", "chuyển đổi", "công nhận", "môn học", "điểm", "học phần", "tương đương"],
        "seed_patterns": [
            "Có được chuyển tín chỉ ngành {program_name} không?",
            "Điều kiện công nhận tín chỉ?",
            "Môn học nào được chuyển đổi tín chỉ?",
            "Thủ tục chuyển tín chỉ như thế nào?",
            "Điểm tín chỉ chuyển đổi tính như thế nào?",
            "Có giới hạn số tín chỉ chuyển đổi không?",
            "Thời gian nộp hồ sơ chuyển tín chỉ?",
            "Tín chỉ từ trường khác có được công nhận không?"
        ]
    },
    {
        "intent_id": "ask_graduation_requirements",
        "intent_name": "Hỏi điều kiện tốt nghiệp",
        "description": "Câu hỏi về các điều kiện để tốt nghiệp",
        "entities_required": ["program_name"],
        "keywords": ["tốt nghiệp", "điều kiện", "yêu cầu", "tín chỉ", "điểm", "khóa luận", "tiếng Anh", "chứng chỉ"],
        "seed_patterns": [
            "Điều kiện tốt nghiệp ngành {program_name}?",
            "Cần bao nhiêu tín chỉ để tốt nghiệp?",
            "Yêu cầu tiếng Anh để tốt nghiệp?",
            "Có phải làm khóa luận không?",
            "Điểm trung bình để tốt nghiệp?",
            "Thời gian tối đa để tốt nghiệp?",
            "Có được tốt nghiệp sớm không?",
            "Chứng chỉ cần thiết để tốt nghiệp?"
        ]
    }
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_intent_questions(intent_category: Dict, num_variations: int = 20) -> List[str]:
    """Generate question variations for a specific intent using OpenAI with retry logic"""
    
    client = openai.AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        timeout=30.0  # Set timeout to 30 seconds
    )
    
    # Get sample entity values for the prompt
    sample_values = {
        "program_name": [
            "Công nghệ thông tin", "Y khoa", "Dược học", "Kinh tế", "Luật",
            "Kỹ thuật xây dựng", "Công nghệ sinh học", "Ngôn ngữ Anh",
            "Công nghệ thông tin (CLC)", "Y khoa (CLC)", "Dược học (CLC)"
        ],
        "program_code": [
            "7480201", "7720101", "7720201", "7340101", "7380101",
            "7480201C", "7720101C", "7720201C"
        ],
        "year": ["2024", "2023", "2022", "năm ngoái", "năm nay", "năm sau"],
        "method_type": [
            "học bạ", "điểm thi THPT", "xét tuyển thẳng",
            "V-SAT", "thi năng lực", "xét tuyển kết hợp"
        ],
        "scholarship_type": [
            "khuyến khích", "tài năng", "vượt khó",
            "doanh nghiệp", "học bổng chính phủ"
        ],
        "dormitory_info": [
            "KTX A", "KTX B", "KTX C", "phòng 2 người",
            "phòng có điều hòa", "phòng có wifi"
        ],
        "campus_name": [
            "Khu I", "Khu II", "Khu III", "Khu Hòa An",
            "cơ sở chính", "Xuân Khánh"
        ]
    }
    
    # Create example questions with real values
    example_questions = []
    
    # Add seed patterns
    if 'seed_patterns' in intent_category:
        for pattern in intent_category['seed_patterns']:
            filled_pattern = pattern
            for entity in intent_category['entities_required']:
                if entity in sample_values:
                    value = sample_values[entity][0]  # Use first sample value
                    filled_pattern = filled_pattern.replace(f"{{{entity}}}", value)
            example_questions.append(filled_pattern)
    
    # Add additional patterns if available
    if intent_category['intent_id'] in additional_patterns:
        for pattern in additional_patterns[intent_category['intent_id']]:
            filled_pattern = pattern
            for entity in intent_category['entities_required']:
                if entity in sample_values:
                    value = sample_values[entity][1]  # Use second sample value
                    filled_pattern = filled_pattern.replace(f"{{{entity}}}", value)
            example_questions.append(filled_pattern)
    
    prompt = f"""
Bạn là chuyên gia tạo dataset câu hỏi cho chatbot tư vấn tuyển sinh Đại học Cần Thơ.

INTENT: {intent_category['intent_name']}
MÔ TẢ: {intent_category['description']}
TỪ KHÓA: {', '.join(intent_category['keywords'])}
ENTITIES: {', '.join(intent_category['entities_required'])}

CÂU HỎI MẪU (đã thay thế entity):
{chr(10).join(f"- {q}" for q in example_questions[:10])}  # Show first 10 examples

YÊU CẦU:
1. Tạo {num_variations} câu hỏi KHÁC NHAU cho intent này
2. Sử dụng ngôn ngữ tự nhiên, đa dạng (formal, informal, viết tắt)
3. Bao gồm cả câu hỏi có lỗi chính tả nhẹ (realistic)
4. Một số câu dùng teen code, viết tắt (e, mình, mk, bao nhiu)
5. Đa dạng cách hỏi: trực tiếp, gián tiếp, lịch sự, thân mật
6. QUAN TRỌNG: Sử dụng các giá trị thực tế cho entities, KHÔNG dùng placeholder
7. Thêm cảm xúc và ngữ cảnh vào câu hỏi (lo lắng, phân vân, hứng thú)
8. Sử dụng từ ngữ phổ biến trong giới trẻ và mạng xã hội
9. Thêm các chi tiết cụ thể liên quan đến CTU
10. Đa dạng độ dài câu hỏi (ngắn, vừa, dài)

VÍ DỤ GIÁ TRỊ THỰC CHO ENTITIES:
{chr(10).join(f"- {entity}: {', '.join(values[:3])}" for entity, values in sample_values.items())}

VÍ DỤ NGÔN NGỮ ĐA DẠNG:
- Formal: "Xin cho biết học phí ngành Công nghệ thông tin là bao nhiêu?"
- Informal: "cho e hỏi học phí ngành Y khoa bao nhiêu ạ"
- Teen: "ngành Dược học hp bao nhiu vậy ạ"
- Typo: "hoc phi nganh cntt la bao nhieu"
- Emotion: "em đang rất lo lắng về học phí ngành Y khoa ạ"
- Context: "em đang phân vân giữa Y khoa CTU và trường khác, cho em hỏi học phí ạ"
- Social: "cho mk hóng xíu học phí ngành CNTT nha"
- Detail: "học phí ngành CNTT chất lượng cao khu 2 là bao nhiêu ạ"

TRẢ LỜI:
Bạn PHẢI trả về một mảng JSON chứa các câu hỏi HOÀN CHỈNH (đã thay thế entity), với format chính xác như sau:
[
  "Học phí ngành Công nghệ thông tin là bao nhiêu?",
  "Mã ngành 7480201 học phí bao nhiêu?",
  "Chi phí học ngành Y khoa CTU?"
]

LƯU Ý:
- Mỗi câu hỏi phải được đặt trong dấu ngoặc kép
- Các câu hỏi phân cách bằng dấu phẩy
- Không có text nào khác ngoài mảng JSON
- Không được có dấu phẩy sau câu hỏi cuối cùng
- KHÔNG được để placeholder như {{program_name}} trong câu hỏi
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia tạo dataset câu hỏi. Bạn CHỈ được phép trả về một mảng JSON chứa các câu hỏi HOÀN CHỈNH (đã thay thế entity), không có text nào khác."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # Increased from 0.7 to 0.8 for more creativity
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean và parse JSON
        try:
            # Loại bỏ markdown code block nếu có
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            # Try to fix common JSON issues
            content = content.replace('\n', ' ').replace('\r', '')
            content = content.replace('""', '"')  # Fix double quotes
            content = content.replace('\\"', '"')  # Fix escaped quotes
            
            # Parse JSON
            questions = json.loads(content)
            if isinstance(questions, list):
                # Validate each question is a string and doesn't contain placeholders
                valid_questions = []
                for q in questions:
                    if isinstance(q, str) and '{' not in q and '}' not in q:
                        valid_questions.append(q)
                    else:
                        print(f"Skipping invalid question: {q[:50]}...")
                
                if valid_questions:
                    return valid_questions
                else:
                    print("Error: No valid questions found")
                    return []
            else:
                print(f"Error: Expected list but got {type(questions)}")
                return []
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw content: {content[:100]}...")
            return []
            
    except Exception as e:
        print(f"Error generating questions for {intent_category['intent_name']}: {e}")
        raise  # Re-raise for retry


async def enrich_with_entity_values(questions: List[str], intent_category: Dict) -> List[Dict]:
    """Replace entity placeholders with real values"""
    
    # Entity value mappings for CTU - expanded list
    entity_values = {
        "program_name": [
            # Chương trình đại trà
            "Công nghệ thông tin", "Y khoa", "Dược học", "Kinh tế",
            "Luật", "Kỹ thuật xây dựng", "Công nghệ sinh học", 
            "Ngôn ngữ Anh", "Quản trị kinh doanh", "Kế toán",
            "Công nghệ thực phẩm", "Thủy sản", "Nông nghiệp",
            "Công nghệ kỹ thuật điện", "Công nghệ kỹ thuật điện tử",
            "Công nghệ kỹ thuật cơ khí", "Công nghệ kỹ thuật hóa học",
            "Công nghệ kỹ thuật môi trường", "Công nghệ kỹ thuật xây dựng",
            "Công nghệ kỹ thuật giao thông", "Công nghệ kỹ thuật cơ điện tử",
            "Công nghệ kỹ thuật điều khiển và tự động hóa", "Công nghệ kỹ thuật máy tính",
            # Chương trình chất lượng cao và tiên tiến
            "Công nghệ sinh học (CTTT)", "Nuôi trồng thủy sản (CTTT)",
            "Thú y (CLC)", "Công nghệ kỹ thuật hóa học (CLC)",
            "Công nghệ thực phẩm (CLC)", "Kỹ thuật xây dựng (CLC)",
            "Kỹ thuật điện (CLC)", "Kỹ thuật điều khiển và tự động hóa (CLC)",
            "Công nghệ thông tin (CLC)", "Kỹ thuật phần mềm (CLC)",
            "Mạng máy tính và truyền thông dữ liệu (CLC)", "Hệ thống thông tin (CLC)",
            "Quản trị kinh doanh (CLC)"
        ],
        "program_code": [
            # Chương trình đại trà
            "7480201",     # Công nghệ thông tin
            "7720101",     # Y khoa
            "7720201",     # Dược học
            "7310101",     # Kinh tế
            "7380101",     # Luật
            "7580201",     # Kỹ thuật xây dựng
            "7420201",     # Công nghệ sinh học
            "7220201",     # Ngôn ngữ Anh
            "7340101",     # Quản trị kinh doanh
            "7340301",     # Kế toán
            "7540101",     # Công nghệ thực phẩm
            "7620301",     # Nuôi trồng thủy sản
            "7620101",     # Nông nghiệp
            "7510301",     # Công nghệ kỹ thuật điện
            "7510302",     # Công nghệ kỹ thuật điện tử
            "7510201",     # Công nghệ kỹ thuật cơ khí
            "7510401",     # Công nghệ kỹ thuật hóa học
            "7510406",     # Công nghệ kỹ thuật môi trường
            "7510102",     # Công nghệ kỹ thuật xây dựng
            "7510104",     # Công nghệ kỹ thuật giao thông
            "7510203",     # Công nghệ kỹ thuật cơ điện tử
            "7510303",     # Công nghệ kỹ thuật điều khiển và tự động hóa
            "7510103",     # Công nghệ kỹ thuật máy tính
            # Chương trình chất lượng cao và tiên tiến
            "7420201T",    # Công nghệ sinh học (CTTT)
            "7620301T",    # Nuôi trồng thủy sản (CTTT)
            "7640101C",    # Thú y (CLC)
            "7510401C",    # Công nghệ kỹ thuật hóa học (CLC)
            "7540101C",    # Công nghệ thực phẩm (CLC)
            "7580201C",    # Kỹ thuật xây dựng (CLC)
            "7520201C",    # Kỹ thuật điện (CLC)
            "7520216C",    # Kỹ thuật điều khiển và tự động hóa (CLC)
            "7480201C",    # Công nghệ thông tin (CLC)
            "7480103C",    # Kỹ thuật phần mềm (CLC)
            "7480102C",    # Mạng máy tính và truyền thông dữ liệu (CLC)
            "7480104C",    # Hệ thống thông tin (CLC)
            "7340101C"     # Quản trị kinh doanh (CLC)
        ],
        "year": [
            "2020", "2021", "2022", "2023", "2024", "2025",
            "năm ngoái", "năm nay", "năm sau", "năm trước",
            "2 năm trước", "3 năm trước", "4 năm trước"
        ],
        "method_type": [
            "học bạ", "điểm thi THPT", "V-SAT", "thi năng lực",
            "xét tuyển thẳng", "ưu tiên xét tuyển", "xét tuyển học bạ",
            "xét tuyển kết hợp", "xét tuyển theo chứng chỉ quốc tế"
        ],
        "scholarship_type": [
            "khuyến khích", "tài năng", "vượt khó", "doanh nghiệp",
            "học bổng chính phủ", "học bổng nước ngoài", "học bổng đối tác",
            "học bổng sinh viên xuất sắc", "học bổng sinh viên nghèo vượt khó"
        ],
        "dormitory_info": [
            "KTX A", "KTX B", "KTX C", "KTX D", "ký túc xá",
            "phòng 2 người", "phòng 4 người", "phòng 6 người",
            "phòng nam", "phòng nữ", "phòng có điều hòa",
            "phòng có wifi", "phòng có nhà bếp", "phòng có ban công"
        ],
        "campus_name": [
            "Khu I", "Khu II", "Khu III", "Khu Hòa An",
            "cơ sở chính", "Xuân Khánh", "Ninh Kiều",
            "Cái Răng", "Thốt Nốt", "Vĩnh Long"
        ],
        "faculty": [
            "Khoa CNTT", "Khoa Y", "Khoa Dược", "Khoa Kinh tế",
            "Khoa Luật", "Khoa Xây dựng", "Khoa Sinh học",
            "Khoa Ngoại ngữ", "Khoa Quản trị", "Khoa Kế toán",
            "Khoa Thủy sản", "Khoa Nông nghiệp", "Khoa Cơ khí",
            "Khoa Điện", "Khoa Điện tử", "Khoa Hóa học",
            "Khoa Môi trường", "Khoa Giao thông"
        ]
    }
    
    enriched_questions = []
    
    for question in questions:
        if '{' in question and '}' in question:
            import re
            placeholders = re.findall(r'\{(\w+)\}', question)
            
            # Increased variations from 3 to 10
            for i in range(min(10, len(entity_values.get(placeholders[0], [])))):
                filled_question = question
                for placeholder in placeholders:
                    if placeholder in entity_values and entity_values[placeholder]:
                        value = entity_values[placeholder][i % len(entity_values[placeholder])]
                        filled_question = filled_question.replace(f"{{{placeholder}}}", value)
                
                enriched_questions.append({
                    "text": filled_question,
                    "entities": placeholders,
                    "is_template": False,
                    "source": "generated"
                })
        else:
            enriched_questions.append({
                "text": question,
                "entities": [],
                "is_template": False,
                "source": "generated"
            })
    
    return enriched_questions


async def generate_intent_dataset():
    """Generate complete intent question dataset for CTU admission chatbot"""
    
    print("🚀 Starting CTU Intent Question Generation...")
    
    dataset = IntentDataset(
        metadata={
            "version": "1.0",
            "created_date": datetime.now().isoformat(),
            "description": "Intent questions for CTU admission chatbot",
            "language": "vi",
            "domain": "university_admission"
        },
        intent_categories=[]
    )
    
    total_questions = 0
    
    for intent_config in CTU_INTENT_CATEGORIES:
        print(f"\n📝 Generating questions for: {intent_config['intent_name']}")
        
        try:
            # Generate variations in smaller batches
            all_questions = []
            batch_size = 100  # Increased from 50 to 100
            num_batches = 10  # Increased from 6 to 10 (1000 questions per intent)
            
            for batch in range(num_batches):
                print(f"   Generating batch {batch + 1}/{num_batches}...")
                batch_questions = await generate_intent_questions(intent_config, num_variations=batch_size)
                all_questions.extend(batch_questions)
                print(f"   Generated {len(batch_questions)} questions in this batch")
                
                # Add longer delay between batches to avoid rate limits
                if batch < num_batches - 1:
                    await asyncio.sleep(5)  # Increased from 2 to 5 seconds
            
            print(f"   Generated {len(all_questions)} raw questions")
            
            # Enrich with entity values
            enriched_questions = await enrich_with_entity_values(
                intent_config['seed_patterns'] + all_questions,
                intent_config
            )
            print(f"   Enriched to {len(enriched_questions)} questions")
            
            # Create IntentCategory object
            intent_category = IntentCategory(
                intent_id=intent_config['intent_id'],
                intent_name=intent_config['intent_name'],
                description=intent_config['description'],
                entities_required=intent_config['entities_required'],
                keywords=intent_config['keywords'],
                questions=[IntentQuestion(**q) for q in enriched_questions]
            )
            
            dataset.intent_categories.append(intent_category)
            total_questions += len(enriched_questions)
            
            # Save intermediate results
            output_dir = Path("output/intent_dataset")
            output_dir.mkdir(exist_ok=True, parents=True)
            
            intermediate_file = output_dir / f"ctu_intent_questions_{intent_config['intent_id']}.json"
            with open(intermediate_file, "w", encoding="utf-8") as f:
                json.dump(intent_category.model_dump(), f, ensure_ascii=False, indent=2)
            
            print(f"   Saved intermediate results to: {intermediate_file}")
            
        except Exception as e:
            print(f"Error processing intent {intent_config['intent_name']}: {e}")
            continue
    
    dataset.total_questions = total_questions
    
    # Save final dataset
    output_dir = Path("output/intent_dataset")
    output_file = output_dir / "ctu_intent_questions.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ DATASET GENERATION COMPLETE!")
    print(f"📊 Statistics:")
    print(f"   - Total intents: {len(dataset.intent_categories)}")
    print(f"   - Total questions: {total_questions}")
    print(f"   - Average per intent: {total_questions / len(dataset.intent_categories):.1f}")
    print(f"   - Saved to: {output_file}")
    
    # Generate summary report
    summary = {
        "generation_date": datetime.now().isoformat(),
        "statistics": {
            "total_intents": len(dataset.intent_categories),
            "total_questions": total_questions,
            "by_intent": {}
        }
    }
    
    for category in dataset.intent_categories:
        summary["statistics"]["by_intent"][category.intent_id] = {
            "name": category.intent_name,
            "question_count": len(category.questions),
            "entities": category.entities_required,
            "keywords": category.keywords
        }
    
    summary_file = output_dir / "generation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"   - Summary saved to: {summary_file}")
    
    return dataset


async def validate_dataset(dataset_file: str):
    """Validate generated dataset for quality and coverage"""
    
    print("\n🔍 Validating dataset...")
    
    with open(dataset_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    issues = []
    
    # Check for duplicate questions
    all_questions = []
    for category in dataset["intent_categories"]:
        for q in category["questions"]:
            if q["text"].lower() in [x.lower() for x in all_questions]:
                issues.append(f"Duplicate: {q['text']}")
            all_questions.append(q["text"])
    
    # Check question length variety
    lengths = [len(q) for q in all_questions]
    avg_length = sum(lengths) / len(lengths)
    
    print(f"\n📊 Validation Results:")
    print(f"   - Total questions: {len(all_questions)}")
    print(f"   - Unique questions: {len(set(q.lower() for q in all_questions))}")
    print(f"   - Average length: {avg_length:.1f} chars")
    print(f"   - Min/Max length: {min(lengths)}/{max(lengths)} chars")
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} issues:")
        for issue in issues[:5]:  # Show first 5
            print(f"   - {issue}")
    else:
        print("\n✅ No issues found!")


def normalize_text(text: str) -> str:
    """Normalize text for comparison to avoid duplicates"""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra spaces
    text = ' '.join(text.split())
    # Remove common variations
    text = text.replace('ctu', 'đại học cần thơ')
    text = text.replace('đhct', 'đại học cần thơ')
    text = text.replace('đại học cần thơ', '')
    return text

def is_similar(text1: str, text2: str, threshold: float = 0.85) -> bool:
    """Check if two texts are similar using sequence matcher"""
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)
    return SequenceMatcher(None, text1, text2).ratio() > threshold

def merge_datasets(existing_file: str, new_file: str, output_file: str):
    """Merge two datasets while avoiding duplicates"""
    print(f"\n🔄 Merging datasets...")
    
    # Load existing dataset
    with open(existing_file, 'r', encoding='utf-8') as f:
        existing = json.load(f)
    
    # Load new dataset
    with open(new_file, 'r', encoding='utf-8') as f:
        new = json.load(f)
    
    # Track unique questions
    unique_questions: Dict[str, Set[str]] = {}
    for intent in existing['intent_categories']:
        unique_questions[intent['intent_id']] = {
            normalize_text(q['text']) for q in intent['questions']
        }
    
    # Merge datasets
    merged = existing.copy()
    total_added = 0
    total_skipped = 0
    
    for new_intent in new['intent_categories']:
        intent_id = new_intent['intent_id']
        
        # Find matching intent in existing dataset
        existing_intent = next(
            (i for i in merged['intent_categories'] if i['intent_id'] == intent_id),
            None
        )
        
        if existing_intent:
            # Add new questions to existing intent
            for question in new_intent['questions']:
                normalized = normalize_text(question['text'])
                
                # Check for duplicates
                is_duplicate = False
                for existing_norm in unique_questions[intent_id]:
                    if is_similar(normalized, existing_norm):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    existing_intent['questions'].append(question)
                    unique_questions[intent_id].add(normalized)
                    total_added += 1
                else:
                    total_skipped += 1
        else:
            # Add new intent
            merged['intent_categories'].append(new_intent)
            unique_questions[intent_id] = {
                normalize_text(q['text']) for q in new_intent['questions']
            }
            total_added += len(new_intent['questions'])
    
    # Update total questions
    merged['total_questions'] = sum(
        len(intent['questions']) for intent in merged['intent_categories']
    )
    
    # Save merged dataset
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Merge complete!")
    print(f"📊 Statistics:")
    print(f"   - Questions added: {total_added}")
    print(f"   - Questions skipped (duplicates): {total_skipped}")
    print(f"   - Total questions: {merged['total_questions']}")
    print(f"   - Saved to: {output_file}")
    
    return merged

async def generate_more_questions(
    intent_category: Dict,
    num_variations: int = 20,
    style_variations: List[str] = None
) -> List[str]:
    """Generate additional question variations with different styles"""
    
    if style_variations is None:
        style_variations = list(style_patterns.keys())
    
    # Get base questions from seed patterns and additional patterns
    base_questions = []
    
    # Add seed patterns
    if 'seed_patterns' in intent_category:
        base_questions.extend(intent_category['seed_patterns'])
    
    # Add additional patterns if available
    if intent_category['intent_id'] in additional_patterns:
        base_questions.extend(additional_patterns[intent_category['intent_id']])
    
    # Add some basic questions from keywords if no patterns
    if not base_questions and 'keywords' in intent_category:
        for keyword in intent_category['keywords']:
            base_questions.append(f"{keyword} ngành {{program_name}}?")
            base_questions.append(f"Thông tin về {keyword} ngành {{program_name}}?")
            base_questions.append(f"Cho hỏi {keyword} ngành {{program_name}}?")
    
    # Replace entities with sample values
    filled_questions = []
    for question in base_questions:
        # Try multiple combinations of entity values
        for i in range(3):  # Generate 3 variations with different values
            filled = question
            for entity in intent_category.get('entities_required', []):
                if entity == 'program_name':
                    values = ["Công nghệ thông tin", "Y khoa", "Dược học", "Kinh tế", "Luật"]
                    filled = filled.replace(f"{{{entity}}}", values[i % len(values)])
                elif entity == 'program_code':
                    values = ["7480201", "7720101", "7720201", "7340101", "7380101"]
                    filled = filled.replace(f"{{{entity}}}", values[i % len(values)])
                elif entity == 'year':
                    values = ["2024", "2023", "2022"]
                    filled = filled.replace(f"{{{entity}}}", values[i % len(values)])
                elif entity == 'method_type':
                    values = ["học bạ", "điểm thi THPT", "xét tuyển thẳng"]
                    filled = filled.replace(f"{{{entity}}}", values[i % len(values)])
                else:
                    filled = filled.replace(f"{{{entity}}}", f"giá trị {entity}")
            filled_questions.append(filled)
    
    # Add style variations
    all_variations = []
    for question in filled_questions:
        # Keep original
        all_variations.append(question)
        
        # Add style variations
        for style in style_variations:
            if style in style_patterns:
                for prefix in style_patterns[style]:
                    # Add prefix if not already similar
                    if not any(is_similar(f"{prefix} {question.lower()}", v) for v in all_variations):
                        variation = f"{prefix} {question.lower()}"
                        all_variations.append(variation)
                        
                        # Add question mark if missing
                        if not variation.endswith('?'):
                            all_variations.append(f"{variation}?")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in all_variations:
        normalized = normalize_text(v)
        if normalized not in seen:
            seen.add(normalized)
            unique_variations.append(v)
    
    return unique_variations[:num_variations]  # Return only requested number of variations

async def enrich_dataset(
    input_file: str,
    output_file: str,
    questions_per_intent: int = 100
):
    """Enrich existing dataset with more variations"""
    
    print(f"\n🔄 Enriching dataset...")
    
    # Load existing dataset
    with open(input_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Add seed patterns if missing
    for intent in dataset['intent_categories']:
        if 'seed_patterns' not in intent:
            # Get seed patterns from CTU_INTENT_CATEGORIES
            matching_intent = next(
                (i for i in CTU_INTENT_CATEGORIES if i['intent_id'] == intent['intent_id']),
                None
            )
            if matching_intent:
                intent['seed_patterns'] = matching_intent['seed_patterns']
            else:
                # Generate basic seed patterns from keywords
                intent['seed_patterns'] = [
                    f"{keyword} ngành {{program_name}}?" 
                    for keyword in intent['keywords'][:3]  # Use first 3 keywords
                ]
                # Add some common patterns
                intent['seed_patterns'].extend([
                    f"Cho em hỏi về {intent['intent_name'].lower()}?",
                    f"Thông tin về {intent['intent_name'].lower()}?",
                    f"Điều kiện {intent['intent_name'].lower()}?"
                ])
    
    # Track unique questions
    unique_questions: Dict[str, Set[str]] = {}
    for intent in dataset['intent_categories']:
        unique_questions[intent['intent_id']] = {
            normalize_text(q['text']) for q in intent['questions']
        }
    
    # Generate more questions for each intent
    total_added = 0
    for intent in dataset['intent_categories']:
        print(f"\n📝 Enriching intent: {intent['intent_name']}")
        
        # Calculate how many more questions needed
        current_count = len(intent['questions'])
        needed = max(0, questions_per_intent - current_count)
        
        if needed > 0:
            try:
                # Generate more questions
                new_questions = await generate_more_questions(
                    intent,
                    num_variations=min(needed // 2, 20),  # Limit to 20 variations per batch
                    style_variations=["formal", "informal", "teen", "typo"]
                )
                
                # Add non-duplicate questions
                added = 0
                for question in new_questions:
                    normalized = normalize_text(question)
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing_norm in unique_questions[intent['intent_id']]:
                        if is_similar(normalized, existing_norm):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        intent['questions'].append({
                            "text": question,
                            "entities": intent.get('entities_required', []),
                            "is_template": False,
                            "source": "enriched"
                        })
                        unique_questions[intent['intent_id']].add(normalized)
                        added += 1
                
                total_added += added
                print(f"   - Added {added} new questions")
                
            except Exception as e:
                print(f"   ⚠️ Error generating questions for {intent['intent_name']}: {e}")
                continue
    
    # Update total questions
    dataset['total_questions'] = sum(
        len(intent['questions']) for intent in dataset['intent_categories']
    )
    
    # Save enriched dataset
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Enrichment complete!")
    print(f"📊 Statistics:")
    print(f"   - Total questions added: {total_added}")
    print(f"   - New total questions: {dataset['total_questions']}")
    print(f"   - Saved to: {output_file}")
    
    return dataset

async def main():
    """Main function to generate and manage intent dataset"""
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Please set OPENAI_API_KEY in .env file")
        return
    
    output_dir = Path("output/intent_dataset")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Check if dataset exists
    existing_file = output_dir / "ctu_intent_questions.json"
    if existing_file.exists():
        # Ask user what to do
        print("\n📂 Found existing dataset!")
        print("What would you like to do?")
        print("1. Generate new dataset")
        print("2. Enrich existing dataset")
        print("3. Merge with new dataset")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            # Generate new dataset
            dataset = await generate_intent_dataset()
            await validate_dataset(str(existing_file))
            
        elif choice == "2":
            # Enrich existing dataset
            enriched_file = output_dir / "ctu_intent_questions_enriched.json"
            dataset = await enrich_dataset(
                str(existing_file),
                str(enriched_file),
                questions_per_intent=500  # Target 500 questions per intent
            )
            await validate_dataset(str(enriched_file))
            
        elif choice == "3":
            # Generate new and merge
            new_file = output_dir / "ctu_intent_questions_new.json"
            dataset = await generate_intent_dataset()
            merged_file = output_dir / "ctu_intent_questions_merged.json"
            dataset = merge_datasets(
                str(existing_file),
                str(new_file),
                str(merged_file)
            )
            await validate_dataset(str(merged_file))
            
        else:
            print("❌ Invalid choice!")
            return
            
    else:
        # Generate new dataset
        dataset = await generate_intent_dataset()
        await validate_dataset(str(existing_file))
    
    print("\n🎉 Dataset management completed!")

if __name__ == "__main__":
    asyncio.run(main()) 