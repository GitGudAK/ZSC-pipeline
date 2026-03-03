import os
import logging
import base64
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

class VideoGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        self.max_retries = config.get("generation", {}).get("video", {}).get("retry_count", 3)
        self.timeout_seconds = 600  # 10 minute timeout per video call
        
    def generate_from_keyframe(self, shot: Shot) -> str:
        if not shot.video_prompt or not shot.keyframe_path:
            logger.warning(f"Shot {shot.id} missing video_prompt or keyframe. Skipping.")
            return shot.clip_path
            
        import requests
        import fal_client
        
        logger.info(f"Generating video for shot {shot.id} using fal.ai (fal-ai/minimax/video-01)...")
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is not set. Cannot use fal.ai")
            return shot.clip_path
        
        # Read keyframe as base64 once
        try:
            if shot.keyframe_path.startswith("gs://"):
                from google.cloud import storage
                bucket_name = shot.keyframe_path.split("/")[2]
                blob_name = "/".join(shot.keyframe_path.split("/")[3:])
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                img_data = blob.download_as_bytes()
            else:
                with open(shot.keyframe_path, "rb") as f:
                    img_data = f.read()
            encoded_image = base64.b64encode(img_data).decode("utf-8")
            image_url = f"data:image/jpeg;base64,{encoded_image}"
        except Exception as e:
            logger.error(f"Failed to read keyframe for shot {shot.id}: {e}")
            return shot.clip_path
            
        for attempt in range(1, self.max_retries + 1):
            try:
                # Set alarm timeout to prevent infinite hangs
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    result = fal_client.run(
                        "fal-ai/minimax/video-01",
                        arguments={
                            "prompt": shot.video_prompt,
                            "image_url": image_url
                        }
                    )
                finally:
                    signal.alarm(0)  # Cancel the alarm
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "video" in result and result["video"] and "url" in result["video"]:
                    video_download_url = result["video"]["url"]
                    
                    vid_resp = requests.get(video_download_url, timeout=120)
                    vid_resp.raise_for_status()
                    
                    filename = f"clips/{shot.id}.mp4"
                    saved_path = self.storage.write_bytes(vid_resp.content, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved fal.ai clip for shot {shot.id} to {saved_path}")
                    return shot.clip_path
                else:
                    logger.error(f"No video returned from fal.ai for shot {shot.id}: {result}")
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timed out after {self.timeout_seconds}s for shot {shot.id}")
                if attempt < self.max_retries:
                    wait = 10 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts timed out for shot {shot.id}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 10 * attempt  # 10s, 20s, 30s
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.clip_path
