from pydantic import BaseModel
from typing import Any, Dict, Optional

class GenerationRequest(BaseModel):
    prompt: str
    model_id: str
    config: Optional[Dict[str, Any]] = None

class GenerationResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
