from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    """
    Request schema for the /analyze endpoint.

    ``raw_input`` is exposed as ``"input"`` in the JSON API so that existing
    callers are unaffected; internally we use ``raw_input`` to avoid shadowing
    the Python builtin ``input()``.
    """

    model_config = {"populate_by_name": True}

    raw_input: str = Field(..., alias="input")  # raw user input (URL, IP, message, etc.)
    source: str = "web"                         # "web" | "api"
    image_base64: Optional[str] = None          # Optional base64 encoded image for OCR
