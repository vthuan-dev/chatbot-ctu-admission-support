from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class QAPair(BaseModel):
    question: str = Field(description="Natural question a student might ask")
    answer: str = Field(description="Comprehensive answer to the question")
    category: str = Field(description="Category like 'admission_methods', 'majors', 'fees', 'contact'")
    priority: int = Field(description="Priority level 1-3, where 1 is most important")

class ExtractedURL(BaseModel):
    url: str = Field(description="Full URL found on the page")
    text: str = Field(description="Link text or description")
    category: str = Field(description="Categorized intent like 'nganh_hoc', 'phuong_thuc_xet_tuyen', etc.")
    priority: int = Field(description="Priority for crawling 1-3, where 1 is highest priority")

class ContactInfo(BaseModel):
    phone: Optional[str] = Field(description="Phone number for admission counseling")
    email: Optional[str] = Field(description="Email for admission inquiries")
    address: Optional[str] = Field(description="Physical address")
    website: Optional[str] = Field(description="Website URL")
    social_media: Optional[Dict[str, str]] = Field(description="Social media links")

class MajorInfo(BaseModel):
    name: str = Field(description="Major name in Vietnamese")
    code: Optional[str] = Field(description="Major code")
    description: Optional[str] = Field(description="Major description")
    category: Optional[str] = Field(description="Major category")
    admission_methods: Optional[List[str]] = Field(description="Available admission methods")

class AdmissionMethod(BaseModel):
    name: str = Field(description="Admission method name")
    description: Optional[str] = Field(description="Method description")
    requirements: Optional[str] = Field(description="Requirements for this method")
    deadline: Optional[str] = Field(description="Application deadline")

class ImportantDate(BaseModel):
    event: str = Field(description="Event name")
    date: str = Field(description="Date or time period")
    description: Optional[str] = Field(description="Additional details")

class AdmissionDataSchema(BaseModel):
    qa_pairs: List[QAPair] = Field(description="Q&A pairs extracted from the page")
    extracted_urls: List[ExtractedURL] = Field(description="URLs found on the page for deeper crawling")
    contact_info: Optional[ContactInfo] = Field(description="Contact information")
    majors: Optional[List[MajorInfo]] = Field(description="Major information")
    admission_methods: Optional[List[AdmissionMethod]] = Field(description="Admission methods")
    important_dates: Optional[List[ImportantDate]] = Field(description="Important dates and deadlines")
    tuition_info: Optional[Dict[str, Any]] = Field(description="Tuition and fee information")
    scholarship_info: Optional[Dict[str, Any]] = Field(description="Scholarship information")
    additional_info: Optional[Dict[str, Any]] = Field(description="Any other relevant information")
    error: bool = Field(default=False, description="Whether there was an error in extraction") 