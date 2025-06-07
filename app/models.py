from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum
import json

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

class AuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    SESSION = "session"

class AuthConfig(BaseModel):
    type: AuthType
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    token_type: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class JobRequest(BaseModel):
    url: HttpUrl
    auth: Optional[AuthConfig] = None
    website_context: Optional[Dict[str, Any]] = None
    user_prompt: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

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
    page_url: Optional[str] = None
    page_title: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class TestStep(BaseModel):
    step_number: int
    action: str
    expected_result: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class TestCase(BaseModel):
    test_case_id: str
    test_case_title: str
    type: str
    priority: str
    description: str
    preconditions: List[str]
    steps: List[TestStep]
    related_element_id: Optional[str] = None
    feature_tested: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class AnalysisResult(BaseModel):
    source_url: str
    analysis_timestamp: datetime
    page_title: str
    identified_elements: List[UIElement]
    generated_test_cases: List[TestCase]
    website_context: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert datetime to ISO format string
        d['analysis_timestamp'] = self.analysis_timestamp.isoformat()
        # Convert any datetime objects in website_context
        if self.website_context:
            d['website_context'] = json.loads(
                json.dumps(self.website_context, cls=DateTimeEncoder)
            )
        return d

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert datetime to ISO format string
        d['created_at'] = self.created_at.isoformat()
        d['updated_at'] = self.updated_at.isoformat()
        return d

class ScanStrategy(BaseModel):
    focus_areas: List[str]
    target_elements_description: List[Dict[str, Any]]
    max_pages_to_scan: int = 5
    page_navigation_rules: Optional[List[Dict[str, Any]]] = None
    scan_depth: int = 1

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class PageNavigationRule(BaseModel):
    source_page: str
    target_pattern: str
    navigation_element: Dict[str, Any]
    wait_for_element: Optional[str] = None
    required_for_flow: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class ElementState(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    DISABLED = "disabled"

class ElementRelation(BaseModel):
    parent_id: Optional[str] = None
    child_ids: List[str] = []
    siblings_ids: List[str] = []

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class ElementMapEntry(BaseModel):
    element_id: str
    element_type: str
    selector: str
    attributes: Dict[str, Any]
    visible_text: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    state: ElementState = ElementState.VISIBLE
    accessibility: Dict[str, Any] = {}
    relations: ElementRelation = ElementRelation()
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    interaction_type: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

class PageElementMap(BaseModel):
    url: str
    timestamp: datetime
    title: str
    elements: List[ElementMapEntry]
    metadata: Dict[str, Any] = {}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert datetime to ISO format string
        d['timestamp'] = self.timestamp.isoformat()
        # Convert any datetime objects in metadata
        if self.metadata:
            d['metadata'] = json.loads(
                json.dumps(self.metadata, cls=DateTimeEncoder)
            )
        return d

class ElementMapCache(BaseModel):
    url: str
    last_updated: datetime
    element_maps: List[PageElementMap]
    version: str = "1.0"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert datetime to ISO format string
        d['last_updated'] = self.last_updated.isoformat()
        return d