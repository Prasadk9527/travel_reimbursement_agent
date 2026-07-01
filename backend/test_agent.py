import json
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import run_agent_streaming
from backend.config import CLAIMS_DIR

def test_all_samples():
    """Test all sample claims and validate outputs."""
    print("🧪 Running Agent Tests...\n")
    print("=" * 60)
    
    results = []
    for claim_file in CLAIMS_DIR.glob("*.json"):
        with open(claim_file, 'r') as f:
            claim = json.load(f)
        
        print(f"\n📋 Testing: {claim_file.stem}")
        print(f"   Employee: {claim.get('employee_name')}")
        print(f"   Amount: ${claim.get('total_amount')}")
        print("-" * 40)
        
        # Run agent
        final_decision = None
        for msg in run_agent_streaming(claim):
            data = json.loads(msg)
            if data.get('type') == 'decision':
                final_decision = data.get('content')
                break
        
        if final_decision:
            print(f"   ✅ Decision: {final_decision.get('decision')}")
            print(f"   📊 Confidence: {final_decision.get('confidence')}")
            print(f"   📝 Explanation: {final_decision.get('explanation')[:100]}...")
            results.append({
                'claim': claim_file.stem,
                'decision': final_decision.get('decision'),
                'confidence': final_decision.get('confidence'),
                'pass': final_decision.get('decision') in ['Approve', 'Partially Approve', 'Reject', 'Manual Review']
            })
        else:
            print(f"   ❌ No decision generated")
            results.append({
                'claim': claim_file.stem,
                'decision': 'FAILED',
                'confidence': 0,
                'pass': False
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("-" * 40)
    passed = sum(1 for r in results if r['pass'])
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    print(f"   Failed: {total - passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    test_all_samples()