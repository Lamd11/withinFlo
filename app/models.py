from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum

class AuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    SESSION = "session"

class AuthConfig(BaseModel):
    type: AuthType
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    token_type: Optional[str] = None  # "cookie" or "bearer"

class JobRequest(BaseModel):
    url: HttpUrl
    auth: Optional[AuthConfig] = None
    website_context: Optional[Dict[str, Any]] = None  # Added for custom context information

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UIElement(BaseModel):
    element_id: str
    element_type: str
    selector: str
    attributes: Dict[str, str]
    visible_text: Optional[str] = None
    position: Optional[Dict[str, int]] = None

class TestStep(BaseModel):
    step_number: int
    action: str
    expected_result: str

class TestCase(BaseModel):
    test_case_id: str
    test_case_title: str
    type: str
    priority: str
    description: str
    preconditions: List[str]
    steps: List[TestStep]
    related_element_id: Optional[str] = None
    feature_tested: Optional[str] = None  # Added to match analyzer's parsing ability

class AnalysisResult(BaseModel):
    source_url: str
    analysis_timestamp: datetime
    page_title: str
    identified_elements: List[UIElement]
    generated_test_cases: List[TestCase]
    website_context: Optional[Dict[str, Any]] = None  # Added for context information

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None 