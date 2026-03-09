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
        negative_prompt = self.config.get("style", {}).get("negative_prompt", "")
        
        # Build style context: setting comes first so it anchors the era/world
        style_parts = []
        if setting:
            style_parts.append(f"SETTING: {setting}")
        if style_guide:
            style_parts.append(f"STYLE: {style_guide}")
        if negative_prompt:
            style_parts.append(f"AVOID: {negative_prompt}")
        style_context = "\n".join(style_parts)
        
        # Create a lookup for character descriptions
        char_lookup = {c.name.lower(): c for c in characters}
        
        # Flatten all shots for narrative context lookups
        all_shots = []
        for scene in scenes:
            all_shots.extend(scene.shots)
        
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
                
                char_context = "\n".join(shot_chars)
                if char_context:
                    char_context = f"Characters in this shot:\n{char_context}"
                
                # Build narrative continuity context
                narrative_ctx = ""
                if shot.narrative_before:
                    narrative_ctx += f"STORY CONTEXT (just before): {shot.narrative_before}\n"
                if shot.narrative_after:
                    narrative_ctx += f"STORY CONTEXT (just after): {shot.narrative_after}\n"
                
                # Use start_visual if available, fallback to description
                start_desc = shot.start_visual or shot.description
                end_desc = shot.end_visual or (
                    f"END OF SHOT — After {shot.camera_movement} has completed. "
                    f"{shot.description} The action has reached its conclusion."
                )
                
                # Format START frame prompt
                shot.image_prompt = self.image_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"{narrative_ctx}ACTION (START FRAME): {start_desc}",
                    location=shot.location,
                    time_of_day=shot.time_of_day,
                    mood=shot.emotion
                ).strip()
                
                # Format END frame prompt
                shot.image_prompt_end = self.image_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"{narrative_ctx}ACTION (END FRAME): {end_desc}",
                    location=shot.location,
                    time_of_day=shot.time_of_day,
                    mood=shot.emotion
                ).strip()
                
                # Format video prompt — includes motion arc from start to end
                motion_arc = ""
                if shot.start_visual and shot.end_visual:
                    motion_arc = (
                        f"\nMOTION ARC: The shot begins with [{shot.start_visual[:120]}...] "
                        f"and ends with [{shot.end_visual[:120]}...]. "
                        f"Animate the transition between these two states smoothly."
                    )
                
                shot.video_prompt = self.video_prompt_template.format(
                    style_guide=style_context,
                    character_descriptions=char_context,
                    shot_description=f"ACTION: {shot.description}{motion_arc}",
                    camera_movement=shot.camera_movement,
                    shot_type=shot.shot_type
                ).strip()
                
        logger.info(f"Successfully wrote prompts for all shots in {len(scenes)} scenes.")
        return scenes
