import os
import logging
import time
import signal
from typing import List, Optional
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("fal.ai call timed out")

class KeyframeGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        self.max_retries = config.get("generation", {}).get("keyframe", {}).get("retry_count", 3)
        self.timeout_seconds = 300  # 5 minute timeout per keyframe call
        
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
            
        for attempt in range(1, self.max_retries + 1):
            try:
                # Set alarm timeout to prevent infinite hangs
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    result = fal_client.run(
                        "fal-ai/nano-banana-2",
                        arguments={
                            "prompt": shot.image_prompt
                        }
                    )
                finally:
                    signal.alarm(0)  # Cancel the alarm
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "images" in result and result["images"]:
                    image_url = result["images"][0]["url"]
                    
                    # Download image
                    img_resp = requests.get(image_url, timeout=60)
                    img_resp.raise_for_status()
                    
                    filename = f"keyframes/{shot.id}.jpg"
                    saved_path = self.storage.write_bytes(img_resp.content, filename)
                    shot.keyframe_path = saved_path
                    logger.info(f"Saved fal.ai keyframe for shot {shot.id} to {saved_path}")
                    return shot.keyframe_path
                else:
                    logger.error(f"No image returned from fal.ai for shot {shot.id}: {result}")
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timed out after {self.timeout_seconds}s for shot {shot.id}")
                if attempt < self.max_retries:
                    wait = 5 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts timed out for shot {shot.id}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 5 * attempt  # 5s, 10s, 15s
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.keyframe_path
