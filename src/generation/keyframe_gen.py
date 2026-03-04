import os
import base64
import logging
import time
import signal
from typing import List, Optional, Dict
from src.utils.gcp_client import GCPClient
from src.utils.storage import StorageManager
from src.models.episode import Shot

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("fal.ai call timed out")

class KeyframeGenerator:
    def __init__(self, gcp_client: GCPClient, config: dict, character_refs: Dict[str, str] = None):
        """
        Args:
            gcp_client: GCP client instance
            config: Pipeline configuration
            character_refs: Dict mapping character name (lowercase) → local image path
        """
        self.client = gcp_client.client
        self.config = config
        self.storage = StorageManager(config)
        self.max_retries = config.get("generation", {}).get("keyframe", {}).get("retry_count", 3)
        self.timeout_seconds = 300  # 5 minute timeout per keyframe call
        self.character_refs = character_refs or {}
        
    def _get_character_data_uri(self, char_name: str) -> Optional[str]:
        """Convert a local character image to a data URI for fal.ai."""
        path = self.character_refs.get(char_name.lower())
        if not path:
            return None
        
        # Resolve relative paths
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
    
    def _collect_character_refs(self, shot: Shot) -> list:
        """Collect data URIs for all characters present in a shot that have references."""
        refs = []
        for char_name in shot.characters_present:
            uri = self._get_character_data_uri(char_name)
            if uri:
                refs.append(uri)
        return refs

    def generate_pair(self, shot: Shot) -> tuple:
        """Generate both start and end keyframes for a shot."""
        import requests
        import fal_client
        
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping pair.")
            return shot.keyframe_path, shot.keyframe_end_path
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY not set.")
            return shot.keyframe_path, shot.keyframe_end_path
        
        char_image_uris = self._collect_character_refs(shot)
        
        # Generate start frame
        logger.info(f"Generating START keyframe for shot {shot.id}...")
        start_path = self._generate_single(
            shot, shot.image_prompt, f"keyframes/{shot.id}_start.jpg",
            char_image_uris, requests, fal_client
        )
        if start_path:
            shot.keyframe_path = start_path
        
        # Generate end frame
        if shot.image_prompt_end:
            logger.info(f"Generating END keyframe for shot {shot.id}...")
            end_path = self._generate_single(
                shot, shot.image_prompt_end, f"keyframes/{shot.id}_end.jpg",
                char_image_uris, requests, fal_client
            )
            if end_path:
                shot.keyframe_end_path = end_path
        
        return shot.keyframe_path, shot.keyframe_end_path

    def _generate_single(self, shot: Shot, prompt: str, filename: str,
                         char_image_uris: list, requests, fal_client) -> Optional[str]:
        """Generate a single keyframe image using nano-banana-2.
        
        If character reference images are provided, uses the /edit endpoint
        with image_urls so the model renders those exact characters.
        Otherwise uses the standard text-to-image endpoint.
        """
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
                        # Use edit endpoint: pass character refs as image_urls
                        result = fal_client.run(model, arguments={
                            "prompt": prompt,
                            "image_urls": char_image_uris,
                        })
                    else:
                        result = fal_client.run(model, arguments={"prompt": prompt})
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "images" in result and result["images"]:
                    image_url = result["images"][0]["url"]
                    img_resp = requests.get(image_url, timeout=60)
                    img_resp.raise_for_status()
                    saved_path = self.storage.write_bytes(img_resp.content, filename)
                    logger.info(f"Saved keyframe to {saved_path} (model: {model})")
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
        
    def generate(self, shot: Shot) -> str:
        """Generate only the start keyframe (legacy single-frame mode)."""
        if not shot.image_prompt:
            logger.warning(f"Shot {shot.id} has no image_prompt. Skipping.")
            return shot.keyframe_path
            
        import requests
        import fal_client
        
        if not os.environ.get("FAL_KEY"):
            logger.error("FAL_KEY environment variable is not set. Cannot use fal.ai")
            return shot.keyframe_path
        
        # Determine which model to use based on character presence
        primary_char = self._find_primary_character(shot)
        
        if primary_char:
            char_data_uri = self._get_character_data_uri(primary_char)
            if char_data_uri:
                return self._generate_with_character(shot, primary_char, char_data_uri, requests, fal_client)
        
        # Default: use nano-banana-2 for shots without character refs
        return self._generate_default(shot, requests, fal_client)
    
    def _generate_with_character(self, shot: Shot, char_name: str, char_image_url: str, requests, fal_client) -> str:
        """Generate keyframe using instant-character model for character consistency."""
        logger.info(f"Generating keyframe for shot {shot.id} using fal-ai/instant-character (character: {char_name})...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
                
                try:
                    result = fal_client.run(
                        "fal-ai/instant-character",
                        arguments={
                            "prompt": shot.image_prompt,
                            "image_url": char_image_url,
                            "image_size": "landscape_16_9",
                            "scale": 1,
                            "guidance_scale": 3.5,
                            "num_inference_steps": 28,
                            "output_format": "jpeg"
                        }
                    )
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "images" in result and result["images"]:
                    image_url = result["images"][0]["url"]
                    
                    img_resp = requests.get(image_url, timeout=60)
                    img_resp.raise_for_status()
                    
                    filename = f"keyframes/{shot.id}.jpg"
                    saved_path = self.storage.write_bytes(img_resp.content, filename)
                    shot.keyframe_path = saved_path
                    logger.info(f"Saved instant-character keyframe for shot {shot.id} (char: {char_name}) to {saved_path}")
                    return shot.keyframe_path
                else:
                    logger.error(f"No image returned from instant-character for shot {shot.id}: {result}")
                    
            except TimeoutError:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timed out for shot {shot.id}")
                if attempt < self.max_retries:
                    wait = 5 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts timed out for shot {shot.id}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for shot {shot.id}: {e}")
                if attempt < self.max_retries:
                    wait = 5 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.keyframe_path
    
    def _generate_default(self, shot: Shot, requests, fal_client) -> str:
        """Generate keyframe using nano-banana-2 (no character ref)."""
        logger.info(f"Generating keyframe for shot {shot.id} using fal.ai (fal-ai/nano-banana-2)...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
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
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                if "images" in result and result["images"]:
                    image_url = result["images"][0]["url"]
                    
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
                    wait = 5 * attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for shot {shot.id}")
            
        return shot.keyframe_path
