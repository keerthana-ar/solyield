from typing import TypedDict, Literal, Optional, List, Dict, Annotated
from operator import add

class State(TypedDict):
    # Session tracking
    session_id: str
    user_role: Literal["agent", "customer", "service_executive", "sales_executive", None]
    
    # Routing & Flow
    support_type: Literal["sales", "service", None]
    messages: Annotated[List[Dict | str], add]
    
    # Authentication
    auth_verified: bool
    auth_step: Literal["identifier", "otp", "verified", "failed", None]
    auth_identifier_type: Literal["email", "phone", None]
    auth_identifier_value: Optional[str]
    auth_otp_sent: Optional[str] # Simulated
    auth_otp_retries: int
    
    # Customer Info (from DB)
    contact: Dict[str, Optional[str]] # Step 8.1: {"email": str | None, "phone": str | None}
    in_db: Optional[bool]
    lookup_retries: int # Added to track Step 5.1 retries
    lookup_retry_choice: Optional[Literal["Try again", "No, continue anyway"]]
    customer_id: Optional[str]
    customer_name: Optional[str]
    location: Optional[str]
    site_id: Optional[str]
    has_proposals: Optional[bool]
    
    # Unregistered System Info (Step 5.2)
    unregistered_system_size: Optional[str]
    unregistered_inverter: Optional[str]
    unregistered_year: Optional[str]
    unregistered_online: Optional[bool]
    unregistered_installer: Optional[str]
    unregistered_system_info: Optional[str]
    
    # Service Information
    issue_flag: Optional[bool]
    issue_text: Optional[str]
    action_text: Optional[str]
    metrics: Optional[List[Dict]]
    selected_issue: Optional[str]
    description: Optional[str]
    photos: List[str]
    ticket_id: Optional[str]
    nps_score: Optional[int]
    service_step: Optional[Literal["system_info", "issue_info", None]] # Added this
    service_resolution_status: Literal["happy", "unhappy", None]
    
    # Sales Information
    sales_profile: Optional[Dict]
    proposals: List[Dict]
    chosen_proposal_id: Optional[str]
    sales_step: Literal["greeting", "review", "context", "segment", "usage", "design", "options", "confirm", None]
    sales_review_choice: Optional[Literal["Review old proposals", "Create new proposals"]]
    sales_review_result: Optional[Literal["Select a proposal", "Generate new options"]]
    chosen_proposal_name: Optional[str]
    
    # New Sales Capture Fields (6.3)
    sales_contact_complement: Optional[str]
    sales_postal_code: Optional[str]
    sales_city: Optional[str]
    sales_segment_choice: Optional[Literal["Residential", "Commercial", "Industrial"]]
    sales_monthly_bill: Optional[str]
    sales_consumption_increase: Optional[str]
    sales_solution_count: Optional[int] # 1-3
    sales_brand_preferences: Optional[List[str]]
    sales_budget_tiers: Optional[List[str]] # Premium, Standard, Budget
    
    # Handoff
    representative_available: Optional[bool]
    handoff_type: Literal["call", "chat", None]
