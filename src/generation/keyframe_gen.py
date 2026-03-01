import os
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class KeyframeGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        
        # Determine the configured provider
        provider = config.get("generation", {}).get("keyframe", {}).get("provider", "nano_banana")
        self.model_id = gcp_client.get_model(provider)
        
        self.storage = StorageManager(config)
        
    def generate(self, shot: Shot) -> str:
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping.")
            return shot.keyframe_path
            
        logger.info(f"Generating keyframe for shot {shot.id} using {self.model_id}...")
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=shot.image_prompt,
                config={"response_modalities": ["IMAGE"]}
            )
            
            # Save the image using StorageManager
            if response.parts and len(response.parts) > 0 and hasattr(response.parts[0], 'image'):
                image = response.parts[0].image
                filename = f"keyframes/{shot.id}.jpg"
                
                if hasattr(image, 'image_bytes'):
                    saved_path = self.storage.write_bytes(image.image_bytes, filename)
                elif hasattr(image, '_bytes'):
                    saved_path = self.storage.write_bytes(image._bytes, filename)
                else: 
                     logger.warning("Could not extract bytes from image part")
                     saved_path = f"error_{shot.id}.jpg"
                     
                shot.keyframe_path = saved_path
                logger.info(f"Saved keyframe for shot {shot.id} to {saved_path}")
            else:
                logger.error(f"No image found in response for shot {shot.id}")
                
        except Exception as e:
            logger.error(f"Error generating keyframe for shot {shot.id}: {e}")
            
        return shot.keyframe_path
