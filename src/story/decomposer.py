import json
import logging
from typing import List
from google.genai import types
from src.utils.gcp_client import GCPClient
from src.models.episode import Scene, Character

logger = logging.getLogger(__name__)

class StoryDecomposer:
    def __init__(self, gcp_client: GCPClient, config: dict):
        self.client = gcp_client.client
        self.model_id = gcp_client.get_model("gemini_pro")
        self.config = config
        
        with open("templates/story_decomposition.txt", "r") as f:
            self.prompt_template = f.read()
            
    def decompose(self, story_text: str, characters: List[Character]) -> List[Scene]:
        episode_config = self.config.get("episode", {})
        style_config = self.config.get("style", {})
        
        char_descriptions = "\\n".join([f"- {c.name}: {c.description}" for c in characters])
        
        # Pydantic schema generation
        json_schema = Scene.model_json_schema()
        
        # Format the prompt
        prompt = self.prompt_template.format(
            style_guide=style_config.get("guide", ""),
            character_descriptions=char_descriptions,
            target_shot_count=episode_config.get("target_shot_count", 120),
            duration=episode_config.get("target_duration_minutes", 20),
            json_schema=json.dumps({"type": "array", "items": json_schema}, indent=2),
            story_text=story_text
        )
        
        logger.info(f"Decomposing story using model {self.model_id} (thinking mode enabled)...")
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=8192),
                temperature=0.3,
            )
        )
        
        try:
            scenes_data = json.loads(response.text)
            scenes = [Scene.model_validate(s) for s in scenes_data]
            logger.info(f"Successfully decomposed story into {len(scenes)} scenes.")
            
            # Simple validation to assign sequential IDs if missing
            shot_counter = 1
            for i, scene in enumerate(scenes):
                if not scene.id:
                    scene.id = f"scene_{i+1:02d}"
                for j, shot in enumerate(scene.shots):
                    if not shot.id:
                        shot.id = f"{scene.id}_shot_{shot_counter:03d}"
                    if not shot.scene_id:
                        shot.scene_id = scene.id
                    shot.order = shot_counter
                    shot_counter += 1
                    
            return scenes
        except Exception as e:
            logger.error(f"Failed to parse or validate decomposer output.\\nError: {e}\\nRaw output: {response.text}")
            raise
