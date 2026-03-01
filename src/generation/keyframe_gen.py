import os
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class KeyframeGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        
        # Determine the configured provider
        provider = config.get("generation", {}).get("keyframe", {}).get("provider", "nano_banana")
        self.model_id = gcp_client.get_model(provider)
        
        self.output_dir = os.path.join(config.get("pipeline", {}).get("output_dir", "./output"), "keyframes")
        os.makedirs(self.output_dir, exist_ok=True)
        
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
            
            # Save the image
            # Different models might return parts differently. Assuming proper mapping in SDK
            if response.parts and len(response.parts) > 0 and hasattr(response.parts[0], 'image'):
                image = response.parts[0].image
                output_path = os.path.join(self.output_dir, f"{shot.id}.jpg")
                
                # Image typically has a bytes attribute or save method
                if hasattr(image, 'save'):
                    image.save(output_path)
                elif hasattr(image, 'image_bytes'):
                    with open(output_path, 'wb') as f:
                        f.write(image.image_bytes)
                elif hasattr(image, '_bytes'):
                    with open(output_path, 'wb') as f:
                        f.write(image._bytes)
                        
                shot.keyframe_path = output_path
                logger.info(f"Saved keyframe for shot {shot.id} to {output_path}")
            else:
                logger.error(f"No image found in response for shot {shot.id}")
                
        except Exception as e:
            logger.error(f"Error generating keyframe for shot {shot.id}: {e}")
            
        return shot.keyframe_path
