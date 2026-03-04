import logging
from typing import List
from src.models.episode import Scene, Character

logger = logging.getLogger(__name__)

class PromptWriter:
    def __init__(self, config: dict):
        self.config = config
        
        with open("templates/image_prompt.txt", "r") as f:
            self.image_prompt_template = f.read()
            
        with open("templates/video_prompt.txt", "r") as f:
            self.video_prompt_template = f.read()
            
    def write_prompts(self, scenes: List[Scene], characters: List[Character]) -> List[Scene]:
        style_guide = self.config.get("style", {}).get("guide", "")
        setting = self.config.get("style", {}).get("setting", "")
        
        # Build style context: setting comes first so it anchors the era/world
        style_parts = []
        if setting:
            style_parts.append(f"SETTING: {setting}")
        if style_guide:
            style_parts.append(f"STYLE: {style_guide}")
        style_context = "\n".join(style_parts)
        
        # Create a lookup for character descriptions
        char_lookup = {c.name.lower(): c for c in characters}
        
        for scene in scenes:
            for shot in scene.shots:
                # Include descriptions only for characters present in the shot
                shot_chars = []
                for char_name in shot.characters_present:
                    char = char_lookup.get(char_name.lower())
                    if char:
                        desc_parts = [f"{char.name}: {char.description}"]
                        if char.reference_images:
                            desc_parts.append("(visual reference provided — maintain character identity)")
                        shot_chars.append(" ".join(desc_parts))
                
                char_context = "\\n".join(shot_chars)
                if char_context:
                    char_context = f"Characters in this shot:\\n{char_context}"
                
                # Format image prompt
                shot.image_prompt = self.image_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"ACTION: {shot.description}",
                    location=shot.location,
                    time_of_day=shot.time_of_day,
                    mood=shot.emotion
                ).strip()
                
                # Format video prompt
                shot.video_prompt = self.video_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"ACTION: {shot.description}",
                    camera_movement=shot.camera_movement,
                    shot_type=shot.shot_type
                ).strip()
                
                # Format end-frame prompt (scene after camera movement / action completes)
                end_description = f"END OF SHOT — After {shot.camera_movement} has completed. {shot.description} The action has reached its conclusion."
                shot.image_prompt_end = self.image_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"ACTION: {end_description}",
                    location=shot.location,
                    time_of_day=shot.time_of_day,
                    mood=shot.emotion
                ).strip()
                
        logger.info(f"Successfully wrote prompts for all shots in {len(scenes)} scenes.")
        return scenes
