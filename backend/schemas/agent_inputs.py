from pydantic import BaseModel
from typing import Optional

class AnalyzeRequest(BaseModel):
    input: str          # raw user input (URL, IP, message, etc.)
    source: str = "web" # "web" | "api"
    image_base64: Optional[str] = None # Optional base64 encoded image for OCR
