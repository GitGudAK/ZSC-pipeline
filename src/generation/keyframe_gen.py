import os
import io
import base64
import logging
import time
import signal
from typing import List, Optional, Dict
from PIL import Image
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("API call timed out")

class KeyframeGenerator:
    """Generates keyframes using Gemini (Vertex AI) as primary, fal.ai as fallback."""
    
    PROVIDER_VERTEX = "vertex"
    PROVIDER_FAL = "fal"
    
    def __init__(self, gcp_client: GCPClient, config: dict, character_refs: Dict[str, str] = None):
        """
        Args:
            gcp_client: GCP client instance (with genai.Client configured for Vertex AI)
            config: Pipeline configuration
            character_refs: Dict mapping character name (lowercase) → local image path
        """
        self.client = gcp_client.client  # google.genai.Client
        self.config = config
        self.storage = StorageManager(config)
        self.max_retries = config.get("generation", {}).get("keyframe", {}).get("retry_count", 3)
        self.timeout_seconds = 300  # 5 minute timeout per keyframe call
        self.character_refs = character_refs or {}
        
        # Provider selection: "vertex" (Gemini via Google subscription) or "fal" (fal.ai)
        provider_cfg = config.get("generation", {}).get("keyframe", {}).get("provider", "nano_banana")
        if provider_cfg in ("fal", "fal_ai"):
            self.provider = self.PROVIDER_FAL
        else:
            self.provider = self.PROVIDER_VERTEX  # default: use Google subscription
        
        # Vertex AI model for image generation
        self.vertex_model = "gemini-2.5-flash-image-preview"
        
    def _load_character_image(self, char_name: str) -> Optional[Image.Image]:
        """Load a character reference as a PIL Image for Vertex AI."""
        path = self.character_refs.get(char_name.lower())
        if not path:
            return None
        if path.startswith('./'):
            path = os.path.join(os.getcwd(), path[2:])
        if not os.path.exists(path):
            logger.warning(f"Character ref image not found: {path}")
            return None
        try:
            return Image.open(path)
        except Exception as e:
            logger.warning(f"Failed to load character image {path}: {e}")
            return None
    
    def _get_character_data_uri(self, char_name: str) -> Optional[str]:
        """Convert a local character image to a data URI (for fal.ai fallback)."""
        path = self.character_refs.get(char_name.lower())
        if not path:
            return None
        if path.startswith('./'):
            path = os.path.join(os.getcwd(), path[2:])
        if not os.path.exists(path):
            logger.warning(f"Character ref image not found: {path}")
            return None
        ext = path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'image/jpeg')
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime};base64,{b64}"
    
    def _collect_character_images(self, shot: Shot) -> List[Image.Image]:
        """Collect PIL Images for all characters in a shot (for Vertex AI)."""
        images = []
        for char_name in shot.characters_present:
            img = self._load_character_image(char_name)
            if img:
                images.append(img)
        return images
    
    def _collect_character_uris(self, shot: Shot) -> list:
        """Collect data URIs for all characters in a shot (for fal.ai fallback)."""
        refs = []
        for char_name in shot.characters_present:
            uri = self._get_character_data_uri(char_name)
            if uri:
                refs.append(uri)
        return refs

    # =====================================================================
    # Public API
    # =====================================================================
    
    def generate_pair(self, shot: Shot) -> tuple:
        """Generate both start and end keyframes for a shot."""
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping pair.")
            return shot.keyframe_path, shot.keyframe_end_path
        
        # Generate start frame
        logger.info(f"Generating START keyframe for shot {shot.id} (provider: {self.provider})...")
        start_path = self._generate_single(shot, shot.image_prompt, f"keyframes/{shot.id}_start.jpg")
        if start_path:
            shot.keyframe_path = start_path
        
        # Generate end frame
        if shot.image_prompt_end:
            logger.info(f"Generating END keyframe for shot {shot.id} (provider: {self.provider})...")
            end_path = self._generate_single(shot, shot.image_prompt_end, f"keyframes/{shot.id}_end.jpg")
            if end_path:
                shot.keyframe_end_path = end_path
        
        return shot.keyframe_path, shot.keyframe_end_path

    def _generate_single(self, shot: Shot, prompt: str, filename: str) -> Optional[str]:
        """Route to the configured provider."""
        if self.provider == self.PROVIDER_VERTEX:
            return self._generate_vertex(shot, prompt, filename)
        else:
            return self._generate_fal(shot, prompt, filename)

    # =====================================================================
    # PRIMARY: Vertex AI (Gemini) — uses Google subscription, no extra cost
    # =====================================================================
    
    def _generate_vertex(self, shot: Shot, prompt: str, filename: str) -> Optional[str]:
        """Generate keyframe using Gemini generate_content with image output.
        
        Supports up to 14 reference images for character consistency.
        Uses gemini-3.1-flash-image-preview model via Vertex AI.
        """
        # Collect character reference images as PIL Images
        char_images = self._collect_character_images(shot)
        
        # Build contents: prompt + any character reference images
        contents = [prompt]
        if char_images:
            contents.extend(char_images)
            logger.info(f"  Including {len(char_images)} character reference image(s)")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    response = self.client.models.generate_content(
                        model=self.vertex_model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_modalities=["TEXT", "IMAGE"],
                            image_config=types.ImageConfig(
                                aspect_ratio="16:9",
                                image_size="2K",
                            ),
                        ),
                    )
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                # Extract the generated image from the response
                if response and response.parts:
                    for part in response.parts:
                        if part.inline_data is not None:
                            # Convert to bytes and save
                            img = part.as_image()
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=95)
                            image_bytes = buf.getvalue()
                            
                            saved_path = self.storage.write_bytes(image_bytes, filename)
                            logger.info(f"Saved keyframe to {saved_path} (Vertex AI: {self.vertex_model})")
                            return saved_path
                
                logger.error(f"No image in Vertex response for {filename}. Response: {response}")
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timed out for {filename}")
                if attempt < self.max_retries:
                    time.sleep(5 * attempt)
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for {filename}: {e}")
                if attempt < self.max_retries:
                    time.sleep(5 * attempt)
        
        return None

    # =====================================================================
    # FALLBACK: fal.ai (nano-banana-2) — requires FAL_KEY, costs per image
    # =====================================================================
    
    def _generate_fal(self, shot: Shot, prompt: str, filename: str) -> Optional[str]:
        """Generate keyframe using fal.ai nano-banana-2.
        
        Uses /edit endpoint with image_urls when character refs exist.
        Falls back to standard text-to-image otherwise.
        """
        import requests
        import fal_client
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY not set. Cannot use fal.ai provider.")
            return None
        
        char_image_uris = self._collect_character_uris(shot)
        
        if char_image_uris:
            model = "fal-ai/nano-banana-2/edit"
        else:
            model = "fal-ai/nano-banana-2"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    if char_image_uris:
                        result = fal_client.run(model, arguments={
                            "prompt": prompt,
                            "image_urls": char_image_uris,
                            "image_size": "landscape_16_9",
                        })
                    else:
                        result = fal_client.run(model, arguments={
                            "prompt": prompt,
                            "image_size": "landscape_16_9",
                        })
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "images" in result and result["images"]:
                    image_url = result["images"][0]["url"]
                    img_resp = requests.get(image_url, timeout=60)
                    img_resp.raise_for_status()
                    saved_path = self.storage.write_bytes(img_resp.content, filename)
                    logger.info(f"Saved keyframe to {saved_path} (fal.ai: {model})")
                    return saved_path
                else:
                    logger.error(f"No image returned for {filename}: {result}")
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timed out for {filename}")
                if attempt < self.max_retries:
                    time.sleep(5 * attempt)
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for {filename}: {e}")
                if attempt < self.max_retries:
                    time.sleep(5 * attempt)
        
        return None

    # =====================================================================
    # Legacy single-frame method (kept for backward compat)
    # =====================================================================
    
    def generate(self, shot: Shot) -> str:
        """Generate only the start keyframe (legacy single-frame mode)."""
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping.")
            return shot.keyframe_path
        
        start_path = self._generate_single(shot, shot.image_prompt, f"keyframes/{shot.id}.jpg")
        if start_path:
            shot.keyframe_path = start_path
        return shot.keyframe_path
