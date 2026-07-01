import sys
import os
import json
from typing import Dict, Any, List

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import POLICY_TEXT, PER_DIEM, PREVIOUS_CLAIMS, MAX_TOTAL
# Now import using absolute path
# from backend.config import POLICY_TEXT, PER_DIEM, PREVIOUS_CLAIMS, MAX_TOTAL
from backend.qdrant_store import QdrantRetriever

# Tool 1: Semantic policy retrieval using Qdrant
def retrieve_policy(query: str) -> str:
    """Retrieve relevant policy sections using semantic search."""
    retriever = QdrantRetriever()
    results = retriever.retrieve(query, top_k=3)
    if not results:
        return "No specific policy found. Using general policy: " + POLICY_TEXT[:200] + "..."
    return "\n".join([f"- {r}" for r in results])

# Tool 2: Receipt completeness check
def check_receipt_completeness(claim: Dict[str, Any]) -> Dict[str, Any]:
    expenses = claim.get("expenses", [])
    missing = []
    for idx, item in enumerate(expenses):
        if not item.get("receipt_attached", False):
            missing.append(f"Item {idx+1}: {item.get('category', 'unknown')} for ${item.get('amount', 0)}")
    complete = len(missing) == 0
    return {
        "complete": complete,
        "missing_items": missing,
        "status": "All receipts present" if complete else f"Missing {len(missing)} receipt(s)"
    }

# Tool 3: Per-diem check
def check_per_diem(claim: Dict[str, Any]) -> Dict[str, Any]:
    city = claim.get("destination_city")
    if not city:
        return {"error": "City not specified"}
    daily_limit = PER_DIEM.get(city, {}).get("meal", 65)
    total_meal = sum(
        item["amount"] for item in claim.get("expenses", [])
        if item.get("category") == "Meals"
    )
    days = claim.get("trip_days", 1)
    allowed = daily_limit * days
    overage = max(0, total_meal - allowed)
    return {
        "city": city,
        "daily_limit": daily_limit,
        "trip_days": days,
        "total_meal_claimed": total_meal,
        "allowed": allowed,
        "overage": overage,
        "within_limit": overage == 0
    }

# Tool 4: Duplicate detection
def check_duplicate(claim: Dict[str, Any]) -> Dict[str, Any]:
    trip_id = claim.get("trip_id")
    if not trip_id:
        return {"duplicate": False, "message": "No trip_id provided – skipping"}
    if trip_id in PREVIOUS_CLAIMS:
        return {
            "duplicate": True,
            "existing_claim_id": PREVIOUS_CLAIMS[trip_id],
            "message": f"Duplicate claim for trip {trip_id} already submitted."
        }
    else:
        PREVIOUS_CLAIMS[trip_id] = claim.get("claim_id", "unknown")
        return {"duplicate": False, "message": "No duplicate found."}

# Tool 5: Approval threshold
def check_approval_threshold(claim: Dict[str, Any]) -> Dict[str, Any]:
    total = claim.get("total_amount", 0)
    exceeds = total > MAX_TOTAL
    return {
        "total": total,
        "threshold": MAX_TOTAL,
        "exceeds_threshold": exceeds,
        "requires_vp_approval": exceeds,
        "message": f"Total ${total} {'exceeds' if exceeds else 'within'} limit of ${MAX_TOTAL}."
    }

# Tool registry
TOOLS = {
    "retrieve_policy": retrieve_policy,
    "check_receipt_completeness": check_receipt_completeness,
    "check_per_diem": check_per_diem,
    "check_duplicate": check_duplicate,
    "check_approval_threshold": check_approval_threshold,
}

def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    func = TOOLS.get(tool_name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = func(**args)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
    
def calculate_confidence(claim: Dict[str, Any], tool_results: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on rule matching.
    Higher confidence = more rules satisfied.
    """
    score = 0.0
    max_score = 5.0
    
    # Check 1: Receipt completeness
    if tool_results.get('receipt', {}).get('complete', False):
        score += 1.0
    
    # Check 2: Per-diem compliance
    if tool_results.get('per_diem', {}).get('within_limit', False):
        score += 1.0
    
    # Check 3: Under threshold
    if not tool_results.get('threshold', {}).get('exceeds_threshold', True):
        score += 1.0
    
    # Check 4: No duplicates
    if not tool_results.get('duplicate', {}).get('duplicate', True):
        score += 1.0
    
    # Check 5: Policy match (semantic similarity)
    if tool_results.get('policy', {}).get('matched', False):
        score += 1.0
    
    confidence = score / max_score
    return round(confidence, 2)    