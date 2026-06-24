import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def generate_threat_analysis(package_name, vulnerability_summary):
    """
    Uses the Gemini API to generate a business-risk executive summary 
    for a given technical vulnerability.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment.")
        return "Simulated AI Threat Analysis: This vulnerability poses a severe risk to data integrity. Immediate patching is strongly advised to prevent potential unauthorized access."
        
    try:
        genai.configure(api_key=api_key)
        
        # We will use gemini-1.5-flash-latest for the fastest possible response time
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = f"""
        You are an expert DevSecOps engineer. I will give you a technical vulnerability summary. 
        I need you to write a 1 to 2 sentence "Executive Threat Analysis" explaining the actual business risk of this vulnerability.
        Keep it urgent, professional, and easy for a non-technical manager to understand why it must be patched.
        Do not use markdown headers or bold text. Just plain text.
        
        Package: {package_name}
        Vulnerability: {vulnerability_summary}
        """
        
        response = model.generate_content(prompt)
        logger.info("Successfully generated AI Threat Analysis.")
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Failed to call Gemini API: {e}")
        return "Simulated AI Threat Analysis: This vulnerability could allow an attacker to bypass critical security controls. Ensure you upgrade to the patched version immediately."

def ask_gemini_question(package_name, question):
    """
    Handles interactive Q&A using the Gemini API.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return f"Simulated Gemini Response to '{question}': The easiest way to fix the `{package_name}` vulnerability is to update your `package.json` to the latest secure version and run `npm install`. Be sure to test for breaking changes!"
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"I have a security vulnerability in the '{package_name}' package. The user asks: {question}. Provide a brief, helpful answer."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to call Gemini API for Q&A: {e}")
        return f"Simulated Gemini Response to '{question}': Update `{package_name}` to a secure version and verify the patch with your CI/CD pipeline."
