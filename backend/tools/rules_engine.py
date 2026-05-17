import json
import os
from typing import List, Dict, Optional, Tuple

class RulesEngine:
    def __init__(self):
        self.rules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules")
        self.suspension_keywords: List[str] = []
        self.phishing_kits: List[Dict[str, str]] = []
        self.load_rules()

    def load_rules(self):
        """Loads JSON rules from the rules directory."""
        try:
            suspension_file = os.path.join(self.rules_dir, "suspension_keywords.json")
            if os.path.exists(suspension_file):
                with open(suspension_file, "r", encoding="utf-8") as f:
                    self.suspension_keywords = json.load(f)
            else:
                self.suspension_keywords = []

            kits_file = os.path.join(self.rules_dir, "phishing_kits.json")
            if os.path.exists(kits_file):
                with open(kits_file, "r", encoding="utf-8") as f:
                    self.phishing_kits = json.load(f)
            else:
                self.phishing_kits = []
                
        except Exception as e:
            print(f"[RulesEngine] Failed to load rules: {e}")

    def scan_for_suspension(self, text: str) -> bool:
        """Scans the text for platform suspension/TOS violation strings."""
        if not text:
            return False
            
        text_lower = text.lower()
        for kw in self.suspension_keywords:
            if kw in text_lower:
                return True
        return False

    def scan_for_phishing_kits(self, html: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Scans raw HTML for known phishing kit DOM signatures.
        Returns (is_match, kit_name, description).
        """
        if not html:
            return False, None, None
            
        html_lower = html.lower()
        for kit in self.phishing_kits:
            if kit["signature"].lower() in html_lower:
                return True, kit["name"], kit["description"]
                
        return False, None, None

# Singleton instance
rules_engine = RulesEngine()
