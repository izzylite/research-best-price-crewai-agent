"""Pydantic output schemas for agent task results to enforce strict JSON outputs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ResearchRetailer(BaseModel):
    vendor: str = Field(..., description="Retailer/vendor name")
    url: Optional[str] = Field(None, description="Direct product URL")
    price: Optional[str] = Field(None, description="Price string as returned by research tool")
    availability: Optional[str] = Field(None, description="Stock status such as 'In stock' or 'Out of stock'")
    notes: Optional[str] = Field(None, description="Additional notes")
    priority: Optional[bool] = Field(False, description="Whether this retailer came from the priority vendor list")


class ResearchResult(BaseModel):
    product_query: str = Field(..., description="Original product query")
    retailers: List[ResearchRetailer] = Field(default_factory=list, description="List of found retailers")
    research_summary: Optional[str] = Field(None, description="Summary of findings")
    total_found: Optional[int] = Field(None, description="Total retailers found")
    research_complete: Optional[bool] = Field(default=True, description="Whether research completed successfully")


class ConfirmationProduct(BaseModel):
    name: str = Field(..., description="Product name as displayed")
    website: Optional[str] = Field(None, description="Retailer website URL or domain")
    url: str = Field(..., description="Direct product page URL")
    price: str = Field(..., description="Price in GBP format")


class ConfirmationSummary(BaseModel):
    search_query: str
    retailer: str 
    confirmation_successful: Optional[bool] = None
    retry_attempt: Optional[int] = None
    feedback_applied: Optional[bool] = None


class ConfirmationResult(BaseModel):
    product: Optional[ConfirmationProduct] = None
    errors: Optional[List[str]] = None
    confirmation_summary: Optional[ConfirmationSummary] = None


class AgentFeedback(BaseModel):
    target_agent: Optional[str] = None
    should_retry: Optional[bool] = None
    priority: Optional[str] = None
    issues: Optional[List[str]] = None
    retry_recommendations: Optional[List[str]] = None
    alternative_retailers: Optional[List[str]] = None
    search_refinements: Optional[List[str]] = None
    confirmation_improvements: Optional[List[str]] = None
    schema_fixes: Optional[List[str]] = None
    # New optional fields to guide ResearchAgent to avoid duplicates
    already_searched_retailers: Optional[List[Dict[str, Any]]] = None
    exclude_retailers: Optional[List[str]] = None  # vendor names
    exclude_domains: Optional[List[str]] = None


class RetryStrategy(BaseModel):
    recommended_approach: Optional[str] = None
    success_probability: Optional[float] = None
    reasoning: Optional[str] = None
    next_steps: Optional[List[str]] = None


class TargetedFeedbackResult(BaseModel):
    search_query: str
    retailer: str
    attempt_number: int
    max_attempts: int
    failure_analysis: Optional[Dict[str, Any]] = None
    research_feedback: Optional[AgentFeedback] = None
    confirmation_feedback: Optional[AgentFeedback] = None
    retry_strategy: Optional[RetryStrategy] = None

