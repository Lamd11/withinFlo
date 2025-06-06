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
    cookie: Optional[Dict[str, str]] = None

class JobRequest(BaseModel):
    url: HttpUrl
    auth: Optional[AuthConfig] = None
    website_context: Optional[Dict[str, Any]] = None  # Added for custom context information
    user_prompt: Optional[str] = None

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Position(BaseModel):
    x: float
    y: float
    width: float
    height: float

class ElementContext(BaseModel):
    parents: List[Dict[str, Any]] = []
    siblings: List[Dict[str, Any]] = []

class ElementMetadata(BaseModel):
    collection: str
    context: Optional[ElementContext] = None
    visibility: Dict[str, Any] = {}
    has_interactive_children: bool = False
    is_navigational: bool = False
    child_count: int = 0

class UIElement(BaseModel):
    element_id: str
    element_type: str
    selector: str
    attributes: Dict[str, Any] = {}
    visible_text: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    metadata: ElementMetadata
    page_url: Optional[str] = None  # URL of the page where the element was found
    page_title: Optional[str] = None  # Title of the page where the element was found

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
    title: str
    expected_results: List[str]
    element_id: str
    element_type: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

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

class ScanStrategy(BaseModel):
    focus_areas: List[str]
    target_elements_description: List[Dict[str, Any]]
    max_pages_to_scan: int = 5  # Default limit to prevent infinite crawling
    page_navigation_rules: List[Dict[str, Any]] = []
    scan_depth: int = 1  # How many levels deep to scan from the initial page