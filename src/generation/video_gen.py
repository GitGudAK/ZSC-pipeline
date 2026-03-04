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
        # Default model: Seedance 1.5 Pro (supports start+end frames, native audio, 4-12s)
        self.model = "fal-ai/bytedance/seedance/v1.5/pro/image-to-video"
        
    def _read_image_as_data_uri(self, path: str) -> Optional[str]:
        """Read a local or GCS image and return as a data URI."""
        try:
            if path.startswith("gs://"):
                from google.cloud import storage
                bucket_name = path.split("/")[2]
                blob_name = "/".join(path.split("/")[3:])
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                img_data = blob.download_as_bytes()
            else:
                with open(path, "rb") as f:
                    img_data = f.read()
            encoded = base64.b64encode(img_data).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            logger.error(f"Failed to read image at {path}: {e}")
            return None
        
    def generate_from_keyframe(self, shot: Shot) -> str:
        if not shot.video_prompt or not shot.keyframe_path:
            logger.warning(f"Shot {shot.id} missing video_prompt or keyframe. Skipping.")
            return shot.clip_path
            
        import requests
        import fal_client
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is not set. Cannot use fal.ai")
            return shot.clip_path
        
        # Read start frame
        start_image_url = self._read_image_as_data_uri(shot.keyframe_path)
        if not start_image_url:
            return shot.clip_path
        
        # Read end frame (optional)
        end_image_url = None
        if shot.keyframe_end_path:
            end_image_url = self._read_image_as_data_uri(shot.keyframe_end_path)
        
        logger.info(f"Generating video for shot {shot.id} using Seedance 1.5 Pro "
                     f"({'start+end' if end_image_url else 'start only'})...")
            
        for attempt in range(1, self.max_retries + 1):
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    arguments = {
                        "prompt": shot.video_prompt,
                        "image_url": start_image_url,
                        "aspect_ratio": "16:9",
                        "resolution": "720p",
                        "duration": str(min(int(shot.duration_seconds), 12)),
                        "generate_audio": True,
                    }
                    
                    if end_image_url:
                        arguments["end_image_url"] = end_image_url
                    
                    result = fal_client.run(self.model, arguments=arguments)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "video" in result and result["video"] and "url" in result["video"]:
                    video_download_url = result["video"]["url"]
                    
                    vid_resp = requests.get(video_download_url, timeout=120)
                    vid_resp.raise_for_status()
                    
                    filename = f"clips/{shot.id}.mp4"
                    saved_path = self.storage.write_bytes(vid_resp.content, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved Seedance clip for shot {shot.id} to {saved_path}")
                    return shot.clip_path
                else:
                    logger.error(f"No video returned for shot {shot.id}: {result}")
                    
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
                    wait = 10 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.clip_path
