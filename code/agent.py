import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel, Field

# Import hybrid_search from retriever
from retriever import hybrid_search

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")

genai.configure(api_key=API_KEY)

# Initialize the model
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
model = genai.GenerativeModel(MODEL_NAME)

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
    """
    Process a single support ticket and return a structured dictionary.
    Includes a two-step generation and self-correction reflection layer.
    """
    try:
        # 1. Search for context
        company_str = company if company and str(company).lower() not in ["none", "nan"] else ""
        subject_str = subject if subject and str(subject).lower() not in ["none", "nan"] else ""
        issue_str = issue if issue else ""
        
        query = f"{company_str} {subject_str} {issue_str}".strip()
        context = hybrid_search(query, top_k=10)
        
        # 2. Prompting
        system_prompt = (
            "You are an AI triage agent for HackerRank, Claude, and Visa.\n"
            "Read the user's issue and the retrieved context below.\n"
            "Base your answer ONLY on the provided context.\n\n"
            "CRITICAL RULES:\n"
            "1. If the context is for the wrong company, or does not contain the answer, or if the issue involves high-risk topics (fraud, PII, account lockouts), you MUST set status to 'escalated' and response to 'Escalated to human support'.\n"
            "2. Write a concise justification for your decision.\n"
            "3. Ensure the product_area is mapped to the most specific sub-folder from our data (e.g., 'billing', 'troubleshooting', 'account-management').\n"
            "4. The status field MUST be exactly 'replied' or 'escalated'.\n"
            "5. The request_type field MUST be exactly 'product_issue', 'feature_request', 'bug', or 'invalid'. Use these strict definitions:\n"
            "   - billing: Any ticket mentioning 'refund', 'payment', 'charge', 'order ID', 'money', 'subscription pause', or 'pricing'.\n"
            "   - bug: Any ticket mentioning 'not working', 'down', 'failing', 'error', 'connectivity issues', or 'site inaccessible'.\n"
            "   - feature_request: Any ticket asking for new capabilities, setup of new integrations (like LTI keys), or 'planning to use' something not yet set up.\n"
            "   - product_issue: General 'how-to' questions, setup guidance, account settings, and usage questions that are NOT bugs or billing.\n"
            "   - invalid: Only for nonsensical, empty, or completely off-topic queries (e.g., questions about movies or unrelated celebrities).\n"
            "   IMPORTANT: Prioritize billing and bug categories if their respective keywords or intents are present.\n\n"
            f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
            f"User Issue: {issue}\n"
            f"Subject: {subject}\n"
            f"Company: {company}\n"
        )
        
        # 3. Generation using structured output
        result = model.generate_content(
            system_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=TicketResponse
            )
        )
        
        # Parse the JSON response
        response_text = result.text
        data = json.loads(response_text)
        
        # 4. Self-Correction Reflection Layer
        reflection_prompt = (
            "You are an auditing AI. Review the following proposed response to a user ticket.\n"
            "Verify three things:\n"
            "1. Is the proposed response 100% grounded ONLY in the provided context?\n"
            "2. Does the company mentioned in the user's ticket match the company in the retrieved documentation?\n"
            "   CRITICAL EXCEPTION: If the company name in the ticket is a reasonable synonym for the context (e.g., 'Claude' vs 'Anthropic' or 'HackerRank' vs 'HackerRank Tech'), do NOT escalate for a mismatch. Only escalate for a company mismatch if the context is clearly for a completely different entity (e.g., using Visa context for a Claude ticket).\n"
            "3. Is the request_type the most accurate choice based on these definitions?\n"
            "   - billing: refund, payment, charge, order ID, money, subscription pause, pricing.\n"
            "   - bug: not working, down, failing, error, connectivity issues, site inaccessible.\n"
            "   - feature_request: new capabilities, setup of new integrations, planning to use something new.\n"
            "   - product_issue: general how-to, setup, account settings, usage that are NOT bugs/billing.\n"
            "   - invalid: nonsensical, empty, off-topic.\n\n"
            f"User Issue: {issue}\n"
            f"Company: {company}\n"
            f"--- PROVIDED CONTEXT ---\n{context}\n--- END CONTEXT ---\n"
            f"--- PROPOSED RESPONSE ---\n{data.get('response')}\n"
            f"--- PROPOSED REQUEST TYPE ---\n{data.get('request_type')}\n--- END PROPOSED RESPONSE ---\n\n"
            "If it is fully grounded, companies match (or are reasonable synonyms), AND the request_type is accurate, output is_grounded: true.\n"
            "If there is any hallucination, assumption, severe company mismatch, or inaccurate request_type, output is_grounded: false."
        )
        
        reflection_result = model.generate_content(
            reflection_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=ReflectionResponse
            )
        )
        
        reflection_data = json.loads(reflection_result.text)
        
        # Override result if reflection fails
        if not reflection_data.get("is_grounded", False):
            data["status"] = "escalated"
            data["response"] = "Escalated to human support"
            data["justification"] = "Self-correction triggered: " + reflection_data.get("reasoning", "Potential hallucination or company mismatch detected.")
        
        # Ensure fallback for strictly typed enums if LLM hallucinations happen
        if data.get("status") not in ["replied", "escalated"]:
            data["status"] = "escalated"
            
        valid_request_types = ["product_issue", "feature_request", "bug", "invalid"]
        if data.get("request_type") not in valid_request_types:
            data["request_type"] = "invalid"
            
        return data

    except Exception as e:
        # Fallback mechanism to ensure evaluation loop never crashes
        print(f"Error processing ticket: {e}")
        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "Escalated due to system error.",
            "justification": "Fallback triggered.",
            "request_type": "invalid"
        }

if __name__ == "__main__":
    # Test execution
    test_issue = "How do I change my profile picture on Claude?"
    test_subject = "Profile Settings"
    test_company = "Claude"
    
    print("Testing process_ticket...")
    result = process_ticket(test_issue, test_subject, test_company)
    print(json.dumps(result, indent=2))
