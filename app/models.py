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
    user_prompt: Optional[str] = None

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
    position: Optional[Dict[str, float]] = None
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
    page_navigation_rules: Optional[List[Dict[str, Any]]] = None  # Rules for navigating between pages
    scan_depth: int = 1  # How many levels deep to scan from the initial page

class PageNavigationRule(BaseModel):
    source_page: str  # URL or identifier of the source page
    target_pattern: str  # URL pattern or identifier of the target page
    navigation_element: Dict[str, Any]  # Element to click/interact with to navigate
    wait_for_element: Optional[str] = None  # Element to wait for on the target page
    required_for_flow: bool = False  # Whether this navigation is required for the test flow