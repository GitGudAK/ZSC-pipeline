import os
import logging
from typing import List, Optional
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class KeyframeGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        
    def generate(self, shot: Shot) -> str:
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping.")
            return shot.keyframe_path
            
        import requests
        import fal_client
        
        logger.info(f"Generating keyframe for shot {shot.id} using fal.ai (fal-ai/nano-banana-2)...")
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is not set. Cannot use fal.ai")
            return shot.keyframe_path
            
        try:
            result = fal_client.subscribe(
                "fal-ai/nano-banana-2",
                arguments={
                    "prompt": shot.image_prompt
                },
                with_logs=True
            )
            
            if "images" in result and result["images"]:
                image_url = result["images"][0]["url"]
                
                # Download image
                img_resp = requests.get(image_url)
                img_resp.raise_for_status()
                
                filename = f"keyframes/{shot.id}.jpg"
                saved_path = self.storage.write_bytes(img_resp.content, filename)
                shot.keyframe_path = saved_path
                logger.info(f"Saved fal.ai keyframe for shot {shot.id} to {saved_path}")
            else:
                logger.error(f"No image returned from fal.ai for shot {shot.id}: {result}")
                
        except Exception as e:
            logger.error(f"Error generating fal.ai keyframe for shot {shot.id}: {e}")
            
        return shot.keyframe_path
