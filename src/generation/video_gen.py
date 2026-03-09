import os
import logging
import base64
import time
from typing import Optional
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Generates video clips from keyframe images.
    
    Supports multiple providers:
    - "veo": Google Veo 2 via fal.ai (fal-ai/veo2/image-to-video) — best for anime
    - "hailuo": Hailuo-02 via fal.ai — good for start+end frame interpolation
    - "vertex_veo": Veo via Vertex AI (direct Google API)
    """
    
    PROVIDER_VEO_FAL = "veo"
    PROVIDER_HAILUO = "hailuo"
    PROVIDER_VERTEX_VEO = "vertex_veo"
    
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        self.max_retries = config.get("generation", {}).get("video", {}).get("retry_count", 3)
        self.timeout_seconds = 600
        
        # Provider selection from config
        provider_cfg = config.get("generation", {}).get("video", {}).get("provider", "veo")
        if provider_cfg in ("hailuo", "minimax"):
            self.provider = self.PROVIDER_HAILUO
        elif provider_cfg == "vertex_veo":
            self.provider = self.PROVIDER_VERTEX_VEO
        else:
            self.provider = self.PROVIDER_VEO_FAL
        
        # Model strings
        self.veo_fal_model = "fal-ai/veo2/image-to-video"
        self.hailuo_model = config.get("generation", {}).get("video", {}).get(
            "hailuo_model", "fal-ai/minimax/hailuo-2.3/pro/image-to-video"
        )
        self.vertex_veo_model = gcp_client.get_model("veo") or "veo-3.1-generate-preview"
        
        # Style configuration for anime enforcement
        self.style_guide = config.get("style", {}).get("guide", "")
        self.negative_prompt = config.get("style", {}).get("negative_prompt", "")
        
        logger.info(f"VideoGenerator initialized with provider: {self.provider}")
        
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

    def _read_image_as_url(self, path: str) -> Optional[str]:
        """Upload a local image to fal CDN and return a URL."""
        try:
            import fal_client
            if path.startswith("gs://"):
                local_path = f"/tmp/veo_input_{int(time.time())}.jpg"
                self.storage.download_to_local(path, local_path)
                path = local_path
            
            url = fal_client.upload_file(path)
            return url
        except Exception as e:
            logger.warning(f"Failed to upload to fal CDN, falling back to data URI: {e}")
            return self._read_image_as_data_uri(path)

    def _build_video_prompt(self, shot: Shot) -> str:
        """Build a video prompt with anime style enforcement."""
        parts = []
        
        # Inject anime style context
        if self.style_guide:
            parts.append(f"Visual style: {self.style_guide}")
        
        # Core motion prompt
        if shot.video_prompt:
            parts.append(shot.video_prompt)
        
        # Camera direction
        if shot.camera_movement and shot.camera_movement not in (shot.video_prompt or ""):
            parts.append(f"Camera: {shot.camera_movement}")
        
        # Anime-specific motion guidance
        parts.append("Anime animation style, cel-shaded, painterly. Smooth deliberate motion.")
        
        return "\n".join(parts)
    
    def generate_from_keyframe(self, shot: Shot) -> str:
        """Generate video clip from a keyframe image. Routes to configured provider."""
        if not shot.video_prompt or not shot.keyframe_path:
            logger.warning(f"Shot {shot.id} missing video_prompt or keyframe. Skipping.")
            return shot.clip_path
        
        if self.provider == self.PROVIDER_VEO_FAL:
            return self._generate_veo_fal(shot)
        elif self.provider == self.PROVIDER_HAILUO:
            return self._generate_hailuo(shot)
        elif self.provider == self.PROVIDER_VERTEX_VEO:
            return self._generate_vertex_veo(shot)
        else:
            logger.error(f"Unknown video provider: {self.provider}")
            return shot.clip_path

    # =====================================================================
    # Veo via fal.ai — Primary provider for anime
    # =====================================================================
    
    def _generate_veo_fal(self, shot: Shot) -> str:
        """Generate video using Veo 2 image-to-video via fal.ai."""
        import requests
        import fal_client
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY not set. Cannot use fal.ai Veo.")
            return shot.clip_path
        
        image_url = self._read_image_as_url(shot.keyframe_path)
        if not image_url:
            logger.error(f"Could not read keyframe for shot {shot.id}")
            return shot.clip_path
        
        prompt = self._build_video_prompt(shot)
        
        logger.info(f"Generating video for shot {shot.id} using Veo (fal.ai)...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = fal_client.subscribe(
                    self.veo_fal_model,
                    arguments={
                        "prompt": prompt,
                        "image_url": image_url,
                        "aspect_ratio": "16:9",
                        "duration": "5s",
                    },
                    with_logs=True,
                )
                
                if result and "video" in result and result["video"] and "url" in result["video"]:
                    video_url = result["video"]["url"]
                    vid_resp = requests.get(video_url, timeout=120)
                    vid_resp.raise_for_status()
                    
                    filename = f"clips/{shot.id}.mp4"
                    saved_path = self.storage.write_bytes(vid_resp.content, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved Veo clip for shot {shot.id} to {saved_path}")
                    return shot.clip_path
                else:
                    logger.error(f"No video returned for shot {shot.id}: {result}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 15 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
        
        return shot.clip_path

    # =====================================================================
    # Hailuo via fal.ai — Supports start+end frame interpolation
    # =====================================================================
    
    def _generate_hailuo(self, shot: Shot) -> str:
        """Generate video using Hailuo-02 via fal.ai."""
        import requests
        import fal_client
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY not set. Cannot use fal.ai Hailuo.")
            return shot.clip_path
        
        start_image_url = self._read_image_as_data_uri(shot.keyframe_path)
        if not start_image_url:
            return shot.clip_path
        
        end_image_url = None
        if shot.keyframe_end_path:
            end_image_url = self._read_image_as_data_uri(shot.keyframe_end_path)
        
        prompt = self._build_video_prompt(shot)
        
        logger.info(f"Generating video for shot {shot.id} using Hailuo-02 "
                     f"({'start+end' if end_image_url else 'start only'})...")
            
        for attempt in range(1, self.max_retries + 1):
            try:
                arguments = {
                    "prompt": prompt,
                    "image_url": start_image_url,
                    "resolution": "1080P",
                    "duration": "6",
                }
                if end_image_url:
                    arguments["end_image_url"] = end_image_url
                
                result = fal_client.run(self.hailuo_model, arguments=arguments)
                
                if "video" in result and result["video"] and "url" in result["video"]:
                    video_url = result["video"]["url"]
                    vid_resp = requests.get(video_url, timeout=120)
                    vid_resp.raise_for_status()
                    
                    filename = f"clips/{shot.id}.mp4"
                    saved_path = self.storage.write_bytes(vid_resp.content, filename)
                    shot.clip_path = saved_path
                    logger.info(f"Saved Hailuo clip for shot {shot.id} to {saved_path}")
                    return shot.clip_path
                else:
                    logger.error(f"No video returned for shot {shot.id}: {result}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 10 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.clip_path

    # =====================================================================
    # Veo via Vertex AI — Direct Google API
    # =====================================================================
    
    def _generate_vertex_veo(self, shot: Shot) -> str:
        """Generate video using Veo via Vertex AI directly."""
        from google.genai import types
        
        try:
            from PIL import Image as PILImage
            if shot.keyframe_path.startswith("gs://"):
                local_path = f"/tmp/veo_kf_{shot.id}.jpg"
                self.storage.download_to_local(shot.keyframe_path, local_path)
                img = PILImage.open(local_path)
            else:
                img = PILImage.open(shot.keyframe_path)
        except Exception as e:
            logger.error(f"Failed to load keyframe for Vertex Veo: {e}")
            return shot.clip_path
        
        prompt = self._build_video_prompt(shot)
        
        logger.info(f"Generating video for shot {shot.id} using Vertex Veo ({self.vertex_veo_model})...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                operation = self.client.models.generate_videos(
                    model=self.vertex_veo_model,
                    prompt=prompt,
                    image=img,
                    config=types.GenerateVideoConfig(
                        aspect_ratio="16:9",
                        number_of_videos=1,
                    ),
                )
                
                while not operation.done:
                    logger.info(f"  Waiting for Veo generation (shot {shot.id})...")
                    time.sleep(15)
                    operation = self.client.operations.get(operation)
                
                if operation.response and operation.response.generated_videos:
                    video = operation.response.generated_videos[0]
                    if hasattr(video, 'video') and video.video:
                        import requests as req
                        if hasattr(video.video, 'uri') and video.video.uri:
                            vid_resp = req.get(video.video.uri, timeout=120)
                            vid_data = vid_resp.content
                        else:
                            vid_data = video.video
                        
                        filename = f"clips/{shot.id}.mp4"
                        saved_path = self.storage.write_bytes(vid_data, filename)
                        shot.clip_path = saved_path
                        logger.info(f"Saved Vertex Veo clip for shot {shot.id} to {saved_path}")
                        return shot.clip_path
                
                logger.error(f"No video in Vertex Veo response for shot {shot.id}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 20 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
        
        return shot.clip_path
