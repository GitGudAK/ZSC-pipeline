import logging
from typing import List
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
import time

logger = logging.getLogger(__name__)

class StyleAnalyzer:
    """Analyzes user-provided images and videos to generate a cohesive style guide prompt."""
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.gcp_client = gcp_client
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        self.model_id = gcp_client.get_model("gemini")
        
        # Determine fallback default style if analysis fails
        self.default_style = config.get("style", {}).get("guide", "Modern anime style, cinematic lighting.")
        
    def _upload_media(self, uri: str):
        """Downloads from GCS if necessary, and uploads to Gemini Files API."""
        try:
            # Stage file locally to upload
            local_path = self.storage.download_to_local(uri, f"/tmp/style_ref_{time.time()}_{uri.split('/')[-1]}")
            if not local_path:
                logger.error(f"Could not stage file {uri} for upload to Gemini.")
                return None
                
            logger.info(f"Uploading style reference to Gemini: {local_path}")
            uploaded_file = self.client.files.upload(file=local_path)
            
            # If it's a video, we might need to wait for processing
            if local_path.lower().endswith(('.mp4', '.mov', '.avi')):
                logger.info(f"Waiting for video {uploaded_file.name} to process in Gemini...")
                while True:
                    file_info = self.client.files.get(name=uploaded_file.name)
                    if file_info.state == "FAILED":
                        logger.error(f"Video processing failed for {uploaded_file.name}")
                        return None
                    if file_info.state == "ACTIVE":
                        break
                    time.sleep(2)
                    
            return uploaded_file
        except Exception as e:
            logger.error(f"Failed to upload media {uri} to Gemini: {e}")
            return None

    def synthesize_style(self, media_uris: List[str]) -> str:
        """Takes a list of media URIs (GCS or local) and generates a unified style prompt."""
        if not media_uris:
            logger.warning("No media URIs provided to StyleAnalyzer. Using default style.")
            return self.default_style
            
        logger.info(f"Analyzing {len(media_uris)} aesthetic references to synthesize a style guide...")
        
        uploaded_parts = []
        for uri in media_uris:
            uploaded = self._upload_media(uri)
            if uploaded:
                uploaded_parts.append(uploaded)
                
        if not uploaded_parts:
            logger.error("Failed to upload any media for style analysis. Falling back to default.")
            return self.default_style
            
        prompt = (
            "You are an expert anime director and visual aesthetician. I am providing you with several "
            "reference images/videos that define the look and feel of my upcoming animated project.\\n\\n"
            "Analyze the aesthetic, color palette, lighting techniques, character design traits, linework, "
            "and general mood of these uploaded materials.\\n\\n"
            "Synthesize a highly detailed, 1-2 paragraph 'Master Style Guide' capturing this exact visual "
            "aesthetic. This guide will be used directly as a prompt suffix for text-to-image AI generators. "
            "Focus strictly on concrete visual descriptors (e.g. 'cinematic neon lighting, cel-shaded characters, "
            "muted cyberpunk color palette, thick linework'). Do NOT describe the content of the images, only the STYLE."
        )
        
        contents = [prompt] + uploaded_parts
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.4, # Keep it analytical and concrete
                )
            )
            
            extracted_style = response.text.strip()
            logger.info("Successfully synthesized Master Style Guide.")
            return extracted_style
            
        except Exception as e:
            logger.error(f"Failed to generate style guide from references: {e}", exc_info=True)
            return self.default_style
