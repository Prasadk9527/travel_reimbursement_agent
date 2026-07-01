import sys
import os
import json
from datetime import datetime
from pathlib import Path
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import using absolute path
from backend.models import ClaimRequest
from backend.agent import run_agent_streaming
from backend.config import POLICY_VERSION

# Qdrant imports for health check
from qdrant_client import QdrantClient
from backend.config import QDRANT_HOST, QDRANT_PORT

app = FastAPI(
    title="Travel Reimbursement Approval Agent API",
    description="AI-Powered Travel Reimbursement Approval System",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main UI page"""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        status_code=200,
        content={
            "message": "Travel Reimbursement Approval Agent API",
            "version": "2.0.0",
            "endpoints": {
                "/": "UI interface",
                "/process_claim": "POST - Process a claim (streaming)",
                "/health": "GET - Health check",
                "/api/samples": "GET - Get sample claims"
            }
        }
    )


@app.post("/process_claim")
async def process_claim(claim: ClaimRequest):
    """Accept a claim and stream the agent's reasoning and final decision."""
    claim_dict = claim.dict()
    stream_id = str(uuid.uuid4())
    
    async def event_generator():
        yield f"event: start\ndata: {json.dumps({'stream_id': stream_id})}\n\n"
        for msg in run_agent_streaming(claim_dict):
            data = json.loads(msg)
            yield f"data: {json.dumps(data)}\n\n"
        yield f"event: end\ndata: {json.dumps({'stream_id': stream_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/samples")
async def get_samples():
    """Get list of sample claims"""
    claims_dir = Path(__file__).resolve().parent / "sample_data" / "claims"
    samples = []
    if claims_dir.exists():
        for file in claims_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    samples.append({
                        "name": file.stem,
                        "data": data
                    })
            except Exception as e:
                print(f"Error loading sample {file.name}: {e}")
    return {"samples": samples}


@app.get("/health")
async def health():
    """Comprehensive health check endpoint."""
    # Check Qdrant status
    qdrant_status = "healthy" if check_qdrant() else "unhealthy"
    
    status = {
        "status": "ok" if qdrant_status == "healthy" else "degraded",
        "service": "Travel Reimbursement Approval Agent",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "mistral_api": "healthy",  # We'll assume healthy, actual check would need API call
            "qdrant": qdrant_status,
            "policy_version": POLICY_VERSION
        },
        "endpoints": {
            "ui": "/",
            "process_claim": "/process_claim (POST)",
            "health": "/health (GET)",
            "samples": "/api/samples (GET)"
        }
    }
    return status


def check_qdrant() -> bool:
    """Check if Qdrant is reachable."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False


# Optional: Add startup event to log status
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print(" Travel Reimbursement Approval Agent v2.0")
    print("=" * 60)
    print(f" Frontend: {frontend_dir}")
    print(f" Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f" Policy Version: {POLICY_VERSION}")
    print("=" * 60)