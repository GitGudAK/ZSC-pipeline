import logging
from google import genai

logger = logging.getLogger(__name__)

class ModelResolver:
    """
    Resolves 'latest' model references to actual model IDs at runtime.
    Queries the Gemini API to find available models, then selects the newest
    version matching the requested capability.
    """
    
    def __init__(self, client: genai.Client):
        self.client = client
        self._cache = {}
        self._available_models = []
        self._fetch_models()
        
    def _fetch_models(self):
        try:
            # Query the Gemini API to find available models
            models_pager = self.client.models.list()
            # Handle potential pagination or list depending on the GenAI SDK version
            if hasattr(models_pager, '__iter__'):
                self._available_models = [m.name for m in models_pager]
            else:
                self._available_models = [m.name for m in getattr(models_pager, 'models', [])]
            logger.info(f"Fetched {len(self._available_models)} models from API")
        except Exception as e:
            logger.warning(f"Failed to fetch models from API: {e}")
            self._available_models = []
    
    def resolve(self, model_type: str, fallback: str) -> str:
        """
        Resolve a model type to the latest available model ID.
        """
        if not self._available_models:
            logger.warning(f"No models fetched, using fallback: {fallback}")
            return fallback
            
        if model_type in self._cache:
            return self._cache[model_type]
            
        resolved_model = fallback
        
        try:
            if model_type == "gemini_pro":
                candidates = [m for m in self._available_models if "pro" in m.lower() and "vision" not in m.lower() and "experimental" not in m.lower()]
                if any("2.5-pro" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "2.5-pro" in m), resolved_model)
                elif any("3.1-pro-preview" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3.1-pro-preview" in m), resolved_model)
                elif any("3.1-pro" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3.1-pro" in m), resolved_model)
                elif any("3-pro" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3-pro" in m), resolved_model)
                    
            elif model_type == "gemini_flash":
                candidates = [m for m in self._available_models if "flash" in m.lower() and "experimental" not in m.lower()]
                if any("3-flash" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3-flash" in m), resolved_model)
                elif any("2.5-flash" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "2.5-flash" in m), resolved_model)
                    
            elif model_type == "veo":
                candidates = [m for m in self._available_models if "veo" in m.lower()]
                if any("3.1" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3.1" in m), resolved_model)
                elif any("3" in m for m in candidates):
                    resolved_model = next((m for m in candidates if "3" in m), resolved_model)
                    
            elif model_type == "imagen":
                # Do not dynamically fetch because Vertex 3.0 quotas are extremely specific per-patch (001 vs 002)
                resolved_model = fallback                    
        except Exception as e:
            logger.warning(f"Error resolving model {model_type}: {e}")
            
        self._cache[model_type] = resolved_model
        logger.info(f"Resolved {model_type} to {resolved_model}")
        return resolved_model
    
    def get_all_resolved(self, config: dict) -> dict:
        """Resolve all model references in config, return mapping of role → model_id."""
        gcp_config = config.get("gcp", {})
        fallback = gcp_config.get("fallback_models", {})
        
        return {
            "gemini_pro": self.resolve("gemini_pro", fallback.get("gemini_pro", "gemini-2.5-pro")),
            "gemini_flash": self.resolve("gemini_flash", fallback.get("gemini_flash", "gemini-2.5-flash")),
            "veo": self.resolve("veo", fallback.get("veo", "veo-3.1-generate-preview")),
            "imagen": self.resolve("imagen", fallback.get("imagen", "imagen-3.0-generate-001")),
            "nano_banana": self.resolve("nano_banana", fallback.get("nano_banana", "imagen-3.0-generate-001"))
        }
