import os
from google import genai
from src.utils.model_resolver import ModelResolver

class GCPClient:
    def __init__(self, config: dict):
        self.config = config
        self.project_id = config.get("gcp", {}).get("project_id", os.environ.get("GCP_PROJECT_ID"))
        self.region = config.get("gcp", {}).get("region", "us-central1")
        
        # Initialize Gemini Client via Vertex AI backend
        self.client = genai.Client(
            vertexai=True, 
            project=self.project_id, 
            location=self.region
        )
        
        self.resolver = ModelResolver(self.client)
        self.resolved_models = self.resolver.get_all_resolved(config)
        
    def get_model(self, model_type: str) -> str:
        """Get the dynamically resolved model ID for a given model type."""
        return self.resolved_models.get(model_type)
