import os
import joblib
import time
import numpy as np
from schemas.agent_outputs import EmailAgentResult

class EmailAgent:
    def __init__(self):
        """Initializes the Email Agent by loading the trained Random Forest model and TF-IDF Vectorizer."""
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "email_model.joblib")
        vectorizer_path = os.path.join(os.path.dirname(__file__), "..", "models", "email_vectorizer.joblib")
        
        try:
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
        except Exception as e:
            print(f"Error loading Email ML model/vectorizer: {e}")
            self.model = None
            self.vectorizer = None

    async def check(self, text: str) -> EmailAgentResult:
        """Analyzes a raw email or text message using the trained ML model."""
        start_time = time.time()
        if self.model is None or self.vectorizer is None:
            return EmailAgentResult(email_score=0.0, finding="Model not loaded.", execution_ms=0)

        try:
            # 1. Vectorize input text
            # The input text typically contains both subject and body in real-world scenarios.
            text_features = self.vectorizer.transform([text])
            
            # 2. Model Inference
            probs = self.model.predict_proba(text_features)[0]
            
            # probs[0] is Ham, probs[1] is Spam/Phishing
            email_score = float(probs[1])
            
            # --- EMAIL HEADER SPOOFING DETECTION ---
            import re
            header_score_boost = 0.0
            header_finding = ""
            
            from_match = re.search(r'^From:\s*(.*)', text, re.IGNORECASE | re.MULTILINE)
            reply_to_match = re.search(r'^Reply-To:\s*(.*)', text, re.IGNORECASE | re.MULTILINE)
            return_path_match = re.search(r'^Return-Path:\s*(.*)', text, re.IGNORECASE | re.MULTILINE)
            
            if from_match:
                def extract_domain(h_str):
                    em = re.search(r'<([^>]+)>', h_str)
                    val = em.group(1) if em else h_str
                    return val.split('@')[-1].strip().lower() if '@' in val else ""
                
                from_domain = extract_domain(from_match.group(1))
                reply_domain = extract_domain(reply_to_match.group(1)) if reply_to_match else ""
                return_domain = extract_domain(return_path_match.group(1)) if return_path_match else ""
                
                if from_domain and reply_domain and from_domain != reply_domain:
                    header_score_boost += 0.40
                    header_finding += f"[Header Spoofing] 'From' domain ({from_domain}) does not match 'Reply-To' ({reply_domain}). "
                if from_domain and return_domain and from_domain != return_domain:
                    header_score_boost += 0.25
                    header_finding += f"[Header Spoofing] 'From' domain ({from_domain}) does not match 'Return-Path' ({return_domain}). "

            email_score = min(email_score + header_score_boost, 1.0)
            threat_type = "phishing" if email_score >= 0.5 else "benign"
            
            # 3. Create finding string
            if header_finding:
                finding = header_finding + f"(Linguistic Risk: {float(probs[1])*100:.1f}%)"
            elif email_score >= 0.75:
                finding = f"High risk content detected ({email_score*100:.1f}% confidence). Strong indicators of phishing or spam."
            elif email_score >= 0.45:
                finding = f"Suspicious content detected ({email_score*100:.1f}% confidence). May contain phishing elements."
            else:
                finding = f"Content appears benign (Phishing risk: {email_score*100:.1f}%)."
            
            return EmailAgentResult(
                email_score=round(email_score, 4),
                threat_type=threat_type,
                finding=finding,
                execution_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            print(f"Email ML Processing Error: {e}")
            return EmailAgentResult(email_score=0.0, finding=f"Processing error: {str(e)}", execution_ms=int((time.time() - start_time) * 1000))
