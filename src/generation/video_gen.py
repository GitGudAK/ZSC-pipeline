import os
import logging
import base64
from typing import List, Optional
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        
    def generate_from_keyframe(self, shot: Shot) -> str:
        if not shot.video_prompt or not shot.keyframe_path:
            logger.warning(f"Shot {shot.id} missing video_prompt or keyframe. Skipping.")
            return shot.clip_path
            
        import requests
        import fal_client
        from google.cloud import storage
        
        logger.info(f"Generating video for shot {shot.id} using fal.ai (fal-ai/minimax/video-01)...")
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is not set. Cannot use fal.ai")
            return shot.clip_path
            
        try:
            image_url = ""
            if shot.keyframe_path.startswith("gs://"):
                bucket_name = shot.keyframe_path.split("/")[2]
                blob_name = "/".join(shot.keyframe_path.split("/")[3:])
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                img_data = blob.download_as_bytes()
                encoded_image = base64.b64encode(img_data).decode("utf-8")
                image_url = f"data:image/jpeg;base64,{encoded_image}"
            else:
                with open(shot.keyframe_path, "rb") as f:
                    img_data = f.read()
                encoded_image = base64.b64encode(img_data).decode("utf-8")
                image_url = f"data:image/jpeg;base64,{encoded_image}"
                
            result = fal_client.subscribe(
                "fal-ai/minimax/video-01",
                arguments={
                    "prompt": shot.video_prompt,
                    "image_url": image_url
                },
                with_logs=True
            )
            
            if "video" in result and result["video"] and "url" in result["video"]:
                video_download_url = result["video"]["url"]
                
                vid_resp = requests.get(video_download_url)
                vid_resp.raise_for_status()
                
                filename = f"clips/{shot.id}.mp4"
                saved_path = self.storage.write_bytes(vid_resp.content, filename)
                shot.clip_path = saved_path
                logger.info(f"Saved fal.ai clip for shot {shot.id} to {saved_path}")
            else:
                logger.error(f"No video returned from fal.ai for shot {shot.id}: {result}")
                
        except Exception as e:
            logger.error(f"Error generating fal.ai video for shot {shot.id}: {e}")
            
        return shot.clip_path
