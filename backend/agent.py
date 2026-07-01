import sys
import os
import json
import re
from typing import Dict, Any, Generator
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import using absolute path
from backend.tools import execute_tool, TOOLS
from backend.config import POLICY_TEXT

load_dotenv()

llm = ChatMistralAI(
    model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
    temperature=0,
    api_key=os.getenv("MISTRAL_API_KEY")
)

AGENT_PROMPT = PromptTemplate.from_template(
    """You are an intelligent travel reimbursement approval agent.
Your task is to evaluate a reimbursement claim and decide: Approve, Partially Approve, Reject, or Manual Review.
You have access to these tools:
{tool_descriptions}

You must follow these steps:
1. Understand the claim details.
2. Use the tools to gather necessary information (policy, receipt completeness, per‑diem, duplicates, approval threshold).
3. Combine the results.
4. Provide a final decision in the exact JSON format below.

### Claim:
{claim}

### Policy Context (for reference):
{policy}

### Your thought process:
First, decide which tools to call. You can call multiple tools, one at a time.
When you want to call a tool, output a line like:
TOOL_CALL: tool_name with args as JSON string, e.g., TOOL_CALL: retrieve_policy {{"query": "hotel limit"}}

After each tool call, you will receive the observation (tool result). Continue until you have all needed information.

Then output your final decision as a JSON object with these keys:
- "decision": one of "Approve", "Partially Approve", "Reject", "Manual Review"
- "approved_amount": number (0 if rejected)
- "deductions": list of strings explaining any reductions
- "rejected_amount": number (amount not approved)
- "missing_documents": list of missing items (if any)
- "policy_references": list of policy rules cited
- "confidence": number between 0 and 1
- "explanation": short summary of reasoning

### Final output must be ONLY the JSON object, no additional text.

Now begin. Use the tools wisely.
"""
)

def run_agent_streaming(claim: Dict[str, Any]) -> Generator[str, None, None]:
    tool_descriptions = "\n".join([f"- {name}: {func.__doc__}" for name, func in TOOLS.items()])
    prompt = AGENT_PROMPT.format(
        tool_descriptions=tool_descriptions,
        claim=json.dumps(claim, indent=2),
        policy=POLICY_TEXT
    )

    chat_history = [HumanMessage(content=prompt)]
    max_iterations = 8
    iteration = 0

    while iteration < max_iterations:
        response = llm.invoke(chat_history)
        response_text = response.content
        chat_history.append(AIMessage(content=response_text))

        yield json.dumps({"type": "step", "content": response_text})

        tool_match = re.search(r'TOOL_CALL:\s*(\w+)\s*({.*})', response_text, re.DOTALL)
        if tool_match:
            tool_name = tool_match.group(1)
            args_str = tool_match.group(2)
            try:
                args = json.loads(args_str)
            except:
                args = {}
            result = execute_tool(tool_name, args)
            yield json.dumps({"type": "tool_call", "tool": tool_name, "args": args_str})
            yield json.dumps({"type": "tool_result", "result": result})

            chat_history.append(HumanMessage(content=f"Tool result: {result}"))
            iteration += 1
            continue

        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                final = json.loads(json_match.group(0))
                required_keys = ["decision", "approved_amount", "deductions", "rejected_amount",
                                 "missing_documents", "policy_references", "confidence", "explanation"]
                if all(k in final for k in required_keys):
                    yield json.dumps({"type": "decision", "content": final})
                    return
        except:
            pass

        chat_history.append(HumanMessage(content="Please provide only the final JSON decision."))
        iteration += 1

    fallback = {
        "decision": "Manual Review",
        "approved_amount": 0,
        "deductions": ["Max iterations reached without final decision"],
        "rejected_amount": claim.get("total_amount", 0),
        "missing_documents": [],
        "policy_references": ["Agent timed out"],
        "confidence": 0.2,
        "explanation": "The agent did not produce a conclusive decision. Manual review needed."
    }
    yield json.dumps({"type": "decision", "content": fallback})

def safe_run_agent(claim: Dict[str, Any]) -> Generator:
    """Run agent with comprehensive error handling."""
    try:
        yield from run_agent_streaming(claim)
    except ConnectionError as e:
        yield json.dumps({
            "type": "error",
            "content": f" Connection Error: {str(e)}. Check Mistral API key."
        })
    except TimeoutError as e:
        yield json.dumps({
            "type": "error",
            "content": f" Timeout Error: {str(e)}. Please try again."
        })
    except Exception as e:
        yield json.dumps({
            "type": "error",
            "content": f" Unexpected Error: {str(e)}"
        })    