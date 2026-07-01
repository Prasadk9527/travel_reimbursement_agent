import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
CLAIMS_DIR = SAMPLE_DATA_DIR / "claims"

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))                 
# Policy versioning
POLICY_VERSION = "1.0.0"
POLICY_LAST_UPDATED = "2026-07-01"

# Track policy changes
POLICY_CHANGELOG = [
    {"version": "1.0.0", "date": "2026-07-01", "changes": "Initial policy"},
]

# Policy text (also loaded from policy.md)
POLICY_TEXT = """
# Travel Reimbursement Policy

1. **Eligible Expenses**:
   - Airfare: Economy class only.
   - Hotel: Up to $200/night, varies by city.
   - Meals: Per‑diem based on destination (see limit table).
   - Transportation: Taxi, ride‑share, public transit.

2. **Approval Rules**:
   - Total claim must not exceed $2,000 without VP approval.
   - All receipts must be attached and legible.
   - Duplicate claims for the same trip are not allowed.
   - Meals exceeding per‑diem are partially approved.

3. **Exceptions**:
   - Any expense over $500 requires manager justification.
   - Claims with missing receipts go to Manual Review.
"""

# Per‑diem and hotel limits
PER_DIEM = {
    "New York": {"meal": 75, "hotel": 250},
    "San Francisco": {"meal": 80, "hotel": 260},
    "Chicago": {"meal": 70, "hotel": 220},
    "Austin": {"meal": 65, "hotel": 200},
}

# Rules
MAX_TOTAL = 2000
VP_APPROVAL_THRESHOLD = 2000
REQUIRED_RECEIPTS = True

# In-memory duplicate store (resets on restart)
PREVIOUS_CLAIMS = {}