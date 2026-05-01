import os
import json
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Import hybrid_search from retriever
from retriever import hybrid_search

# Load environment variables
load_dotenv()

# Configure OpenRouter API
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables. Please check your .env file.")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# Initialize the model (UPDATED TO GPT-OSS)
MODEL_NAME = "openai/gpt-oss-120b:free"

class TicketResponse(BaseModel):
    status: str = Field(description="Must be 'replied' or 'escalated'")
    product_area: str = Field(description="The most relevant support category or domain area")
    response: str = Field(description="A user-facing answer grounded in the support corpus")
    justification: str = Field(description="A concise explanation of the decision & response")
    request_type: str = Field(description="Must be 'product_issue', 'feature_request', 'bug', or 'invalid'")

class ReflectionResponse(BaseModel):
    is_grounded: bool = Field(description="True if the response is fully grounded, company matches, and request_type is accurate.")
    reasoning: str = Field(description="Explanation of why it is or isn't valid.")

def process_ticket(issue: str, subject: str, company: str) -> dict:
    try:
        company_str = company if company and str(company).lower() not in ["none", "nan"] else ""
        subject_str = subject if subject and str(subject).lower() not in ["none", "nan"] else ""
        issue_str = issue if issue else ""
        
        query = f"{company_str} {subject_str} {issue_str}".strip()
        context = hybrid_search(query, top_k=5)
        
        system_prompt = (
            "You are an AI triage agent for HackerRank, Claude, and Visa.\n"
            'You must return ONLY a raw JSON object matching this structure: {"status": "...", "product_area": "...", "response": "...", "justification": "...", "request_type": "..."}\n'
            "Read the user's issue and the retrieved context below.\n"
            "Base your answer ONLY on the provided context.\n\n"
            "CRITICAL RULES:\n"
            "1. If the context is for the wrong company, or does not contain the answer, or if the issue involves high-risk topics (fraud, PII, account lockouts), you MUST set status to 'escalated' and response to 'Escalated to human support'.\n"
            "2. Write a concise justification for your decision.\n"
            "3. Ensure the product_area is mapped to the most specific sub-folder from our data (e.g., 'billing', 'troubleshooting', 'account-management').\n"
            "4. The status field MUST be exactly 'replied' or 'escalated'.\n"
            "5. The request_type field MUST be chosen using this STRICT EVALUATION ORDER:\n"
            "   - STEP 1: Is it a 'bug'? (Look for keywords: error, broken, site down, failing, crashed, 404). If yes, return 'bug'.\n"
            "   - STEP 2: Is it a 'feature_request'? (Look for keywords: new feature, wish, please add, planning to use, integration setup). If yes, return 'feature_request'.\n"
            "   - STEP 3: Is it 'invalid'? (Spam, nonsensical, completely empty, or off-topic like movies/celebrities). If yes, return 'invalid'.\n"
            "   - STEP 4: If and ONLY if it fails ALL of the above checks, return 'product_issue' (Use this for refunds, billing, score disputes, how-tos, and account settings).\n\n"
            f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
            f"User Issue: {issue}\n"
            f"Subject: {subject}\n"
            f"Company: {company}\n"
        )
        
        for attempt in range(2):
            try:
                result = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": system_prompt}],
                    temperature=0.0,
                    timeout=60
                )
                break
            except Exception as e:
                if attempt == 0:
                    print("API Timeout, retrying in 5s...")
                    time.sleep(5)
                else:
                    print("API Failed, using fallback")
                    raise e
        
        text = result.choices[0].message.content
        match = re.search(r'\{.*\}', text, re.DOTALL)
        response_text = match.group(0) if match else text
        data = json.loads(response_text)
        
        reflection_prompt = (
            "You are an auditing AI. Review the following proposed response to a user ticket.\n"
            "Verify three things:\n"
            "1. Is the proposed response 100% grounded ONLY in the provided context?\n"
            "2. Does the company mentioned in the user's ticket match the company in the retrieved documentation?\n"
            "   CRITICAL EXCEPTION: If the company name is a reasonable synonym (e.g., 'Claude' vs 'Anthropic'), do NOT escalate.\n"
            "3. Is the request_type accurate based on these definitions: bug, feature_request, invalid, product_issue?\n\n"
            f"User Issue: {issue}\n"
            f"Company: {company}\n"
            f"--- PROVIDED CONTEXT ---\n{context}\n--- END CONTEXT ---\n"
            f"--- PROPOSED RESPONSE ---\n{data.get('response')}\n"
            f"--- PROPOSED REQUEST TYPE ---\n{data.get('request_type')}\n--- END PROPOSED RESPONSE ---\n\n"
            "If grounded, companies match, and request_type accurate, output: true.\n"
            "Otherwise, output: false.\n"
            'You must return ONLY a raw JSON object matching this structure: {"is_grounded": true/false, "reasoning": "..."}'
        )
        
        for attempt in range(2):
            try:
                reflection_result = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": reflection_prompt}],
                    temperature=0.0,
                    timeout=60
                )
                break
            except Exception as e:
                if attempt == 0:
                    print("API Timeout, retrying in 5s...")
                    time.sleep(5)
                else:
                    print("API Failed, using fallback")
                    raise e
        
        ref_text = reflection_result.choices[0].message.content
        ref_match = re.search(r'\{.*\}', ref_text, re.DOTALL)
        reflection_text = ref_match.group(0) if ref_match else ref_text
        reflection_data = json.loads(reflection_text)
        
        is_grounded = reflection_data.get("is_grounded", False)
        if str(is_grounded).lower() not in ["true", "1", "yes"]:
            data["status"] = "escalated"
            data["justification"] = "Self-correction triggered: " + str(reflection_data.get("reasoning", "Potential hallucination detected."))
        
        status_val = str(data.get("status", "")).lower().strip()
        data["status"] = status_val if status_val in ["replied", "escalated"] else "escalated"
            
        valid_request_types = ["product_issue", "feature_request", "bug", "invalid"]
        req_type = str(data.get("request_type", "")).lower().strip()
        data["request_type"] = req_type if req_type in valid_request_types else "invalid"
            
        return data

    except Exception as e:
        print(f"Error processing ticket: {e}")
        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "Escalated due to system error.",
            "justification": "Fallback triggered.",
            "request_type": "invalid"
        }

if __name__ == "__main__":
    test_issue = "How do I change my profile picture on Claude?"
    result = process_ticket(test_issue, "Profile Settings", "Claude")
    print(json.dumps(result, indent=2))