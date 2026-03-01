import os
import time
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        
        provider = config.get("generation", {}).get("video", {}).get("provider", "veo")
        self.model_id = gcp_client.get_model(provider)
        
        self.storage = StorageManager(config)
        
    def generate_from_keyframe(self, shot: Shot) -> str:
        if not shot.video_prompt or not shot.keyframe_path:
            logger.warning(f"Shot {shot.id} missing video_prompt or keyframe. Skipping.")
            return shot.clip_path
            
        logger.info(f"Generating video for shot {shot.id} using {self.model_id}...")
        
        try:
            # Download image locally first if it's in GCS to upload to Gemini File API
            logger.info(f"Staging keyframe {shot.keyframe_path}...")
            local_kf = self.storage.download_to_local(shot.keyframe_path, f"/tmp/{shot.id}_kf.jpg")
            
            uploaded_image = self.client.files.upload(file=local_kf)
            
            config_params = {"resolution": self.config.get("episode", {}).get("resolution", "1080p")}
            
            operation = self.client.models.generate_videos(
                model=self.model_id,
                prompt=shot.video_prompt,
                image=uploaded_image,
                config=types.GenerateVideosConfig(**config_params),
            )
            
            # Poll until done
            logger.info(f"Waiting for video generation of shot {shot.id} to complete...")
            while not operation.done:
                time.sleep(10)
                operation = self.client.operations.get(operation=operation)
                
            if hasattr(operation.response, 'generated_videos') and operation.response.generated_videos:
                video_obj = operation.response.generated_videos[0]
                filename = f"clips/{shot.id}.mp4"
                
                # Retrieve the contents of the generated video
                if hasattr(video_obj, "video_bytes") and video_obj.video_bytes:
                    saved_path = self.storage.write_bytes(video_obj.video_bytes, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved clip for shot {shot.id} to {saved_path}")
                elif hasattr(video_obj, "uri") and video_obj.uri:
                    import requests
                    r = requests.get(video_obj.uri)
                    saved_path = self.storage.write_bytes(r.content, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved clip for shot {shot.id} to {saved_path}")
                else:
                    logger.error(f"Cannot decode generated video content for shot {shot.id}")
            else:
                logger.error(f"No video generated for shot {shot.id}")
                
        except Exception as e:
            logger.error(f"Error generating video for shot {shot.id}: {e}")
            
        return shot.clip_path
