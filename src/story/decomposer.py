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
        
        char_descriptions = "\n".join([f"- {c.name}: {c.description}" for c in characters])
        
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
            
            # ── POST-PROCESSING: backfill narrative context & validate visuals ──
            scenes = self._postprocess_shots(scenes)
                    
            return scenes
        except Exception as e:
            logger.error(f"Failed to parse or validate decomposer output.\nError: {e}\nRaw output: {response.text}")
            raise
    
    def _postprocess_shots(self, scenes: List[Scene]) -> List[Scene]:
        """Post-process decomposed shots to ensure narrative continuity fields are populated.
        
        1. Backfill narrative_before/narrative_after from adjacent shots if Gemini missed them.
        2. Derive start_visual/end_visual from description + camera_movement if missing.
        3. Cross-validate that end_visual of shot N is coherent with start_visual of shot N+1
           within the same scene (log warnings, don't block).
        """
        # Flatten all shots in order for cross-shot context
        all_shots = []
        for scene in scenes:
            all_shots.extend(scene.shots)
        
        for i, shot in enumerate(all_shots):
            # ── Backfill narrative_before ──
            if not shot.narrative_before:
                if i == 0:
                    shot.narrative_before = "The story is about to begin."
                else:
                    prev = all_shots[i - 1]
                    shot.narrative_before = prev.description
                    
            # ── Backfill narrative_after ──
            if not shot.narrative_after:
                if i == len(all_shots) - 1:
                    shot.narrative_after = "The scene lingers as the episode draws to a close."
                else:
                    nxt = all_shots[i + 1]
                    shot.narrative_after = nxt.description
            
            # ── Derive start_visual from description if missing ──
            if not shot.start_visual:
                shot.start_visual = (
                    f"{shot.shot_type} of {shot.description}. "
                    f"Location: {shot.location}. Time: {shot.time_of_day}. "
                    f"Mood: {shot.emotion}."
                )
                logger.warning(f"Shot {shot.id}: start_visual was empty, derived from description.")
            
            # ── Derive end_visual from description + camera if missing ──
            if not shot.end_visual:
                if shot.camera_movement and shot.camera_movement.lower() != "static":
                    shot.end_visual = (
                        f"After {shot.camera_movement}: {shot.description}. "
                        f"The movement has completed, revealing the final composition. "
                        f"Location: {shot.location}. Time: {shot.time_of_day}. "
                        f"Mood: {shot.emotion}."
                    )
                else:
                    # Static shot — end visual should show evolved state
                    shot.end_visual = (
                        f"Same framing as start, but the action has progressed: {shot.description}. "
                        f"Characters' expressions and poses reflect the emotional shift. "
                        f"Location: {shot.location}. Mood: {shot.emotion}."
                    )
                logger.warning(f"Shot {shot.id}: end_visual was empty, derived from description + camera.")
        
        # ── Cross-shot continuity warnings ──
        for i in range(len(all_shots) - 1):
            curr = all_shots[i]
            nxt = all_shots[i + 1]
            # Same scene → visual continuity should hold
            if curr.scene_id == nxt.scene_id:
                if curr.location != nxt.location:
                    logger.warning(
                        f"Continuity: shots {curr.id} → {nxt.id} are in the same scene "
                        f"but locations differ ({curr.location} → {nxt.location})"
                    )
        
        backfill_count = sum(1 for s in all_shots if s.start_visual and s.end_visual)
        logger.info(f"Post-processing complete: {backfill_count}/{len(all_shots)} shots have start+end visuals.")
        
        return scenes
