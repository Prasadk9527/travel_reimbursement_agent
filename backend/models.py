from pydantic import BaseModel, Field
from typing import List, Optional

class Expense(BaseModel):
    category: str
    amount: float
    receipt_attached: bool = False

class ClaimRequest(BaseModel):
    claim_id: str
    employee_name: str
    trip_id: str
    destination_city: str
    trip_days: int = 1
    total_amount: float
    expenses: List[Expense]

class DecisionResponse(BaseModel):
    decision: str  # Approve, Partially Approve, Reject, Manual Review
    approved_amount: float
    deductions: List[str]
    rejected_amount: float
    missing_documents: List[str]
    policy_references: List[str]
    confidence: float  # 0-1
    explanation: str