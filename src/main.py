import os
import json
import logging
import click
import yaml
from typing import Optional, Dict

from src.utils.gcp_client import GCPClient
from src.models.episode import Episode, Scene, Character
from src.story.decomposer import StoryDecomposer
from src.story.prompt_writer import PromptWriter
from src.generation.keyframe_gen import KeyframeGenerator
from src.generation.video_gen import VideoGenerator
from src.assembly.stitcher import Stitcher
from src.utils.storage import StorageManager
from src.story.style_analyzer import StyleAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    base_config = {}
    default_path = "config/default_config.yaml"
    if os.path.exists(default_path):
        with open(default_path, "r") as f:
            base_config = yaml.safe_load(f) or {}
            
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
            for k, v in user_config.items():
                if isinstance(v, dict) and k in base_config and isinstance(base_config[k], dict):
                    base_config[k].update(v)
                else:
                    base_config[k] = v
    # Simple env var substitution for string values
    def replace_env_vars(d):
        for k, v in d.items():
            if isinstance(v, dict):
                replace_env_vars(v)
            elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                d[k] = os.environ.get(env_key, v)

    replace_env_vars(base_config)
    return base_config

def save_state(storage: StorageManager, episode: Episode, path: str):
    storage.write_json(episode.model_dump(mode='json'), path)

def load_state(storage: StorageManager, path: str) -> Episode:
    data = storage.read_json(path)
    if data:
        return Episode.model_validate(data)
    raise FileNotFoundError(f"State file not found at {path}")

def load_character_refs() -> tuple[list, Dict[str, str]]:
    """Load character manifest from output/characters/manifest.json.
    Returns (characters_list, char_refs_dict).
    characters_list: list of Character model dicts for Episode.
    char_refs_dict: name(lowercase) → image_path for KeyframeGenerator.
    """
    manifest_path = os.path.join("output", "characters", "manifest.json")
    if not os.path.exists(manifest_path):
        return [], {}
    
    try:
        with open(manifest_path, "r") as f:
            entries = json.load(f)
    except Exception:
        return [], {}
    
    characters = []
    char_refs = {}
    for entry in entries:
        name = entry.get("name", "")
        desc = entry.get("description", "")
        img_path = entry.get("imagePath", "")
        
        characters.append(Character(name=name, description=desc, reference_images=[img_path]))
        if img_path:
            char_refs[name.lower()] = img_path
    
    logger.info(f"Loaded {len(char_refs)} character references: {list(char_refs.keys())}")
    return characters, char_refs

@click.group()
def cli():
    """AI Anime Production Pipeline"""
    pass

@cli.command()
@click.option("--config", required=True, help="Path to episode config YAML")
@click.option("--story", required=True, help="Path to story text file")
@click.option("--style-refs", default=None, help="Comma-separated list of image/video style references")
@click.option("--style-guide", default=None, help="Override style guide text (from style inference)")
@click.option("--style-setting", default=None, help="Override setting/era text (from style inference)")
def run(config: str, story: str, style_refs: str, style_guide: str, style_setting: str):
    """Run full pipeline end-to-end"""
    logger.info("Starting Full Pipeline Run")
    cfg = load_config(config)
    gcp_client = GCPClient(cfg)
    storage = StorageManager(cfg)
    
    # Apply style overrides from style inference step
    if style_guide:
        cfg.setdefault("style", {})["guide"] = style_guide
        logger.info(f"Style guide overridden from inference: {style_guide[:80]}...")
    if style_setting:
        cfg.setdefault("style", {})["setting"] = style_setting
        logger.info(f"Style setting overridden from inference: {style_setting[:80]}...")
    
    with open(story, "r") as f:
        story_text = f.read()
        
    ep_data = cfg.get("episode", {})
    chars_data = cfg.get("characters", [])
    
    # Load character references from manifest
    manifest_chars, char_refs = load_character_refs()
    if manifest_chars:
        # Merge manifest characters with config characters
        chars_data = [c.model_dump() if hasattr(c, 'model_dump') else c for c in manifest_chars]
        logger.info(f"Using {len(manifest_chars)} characters from manifest")
    
    # Visual Style Analysis (Phase 3)
    refs_list = [r.strip() for r in style_refs.split(",")] if style_refs else []
    
    if refs_list and not style_guide:
        # Only run style analysis from refs if no style_guide override was provided
        analyzer = StyleAnalyzer(gcp_client, cfg)
        unified_style = analyzer.synthesize_style(refs_list)
        logger.info(f"Synthesized dynamic style guide from references.")
    else:
        unified_style = cfg.get("style", {}).get("guide", "")
    
    episode = Episode(
        title=ep_data.get("title", "Unknown"),
        episode_number=ep_data.get("episode_number", 1),
        total_duration_target=ep_data.get("target_duration_minutes", 20.0),
        synopsis=ep_data.get("synopsis", ""),
        characters=chars_data,
        style_guide=unified_style
    )
    
    state_file = cfg.get("pipeline", {}).get("state_file", "output/pipeline_state.json")
    
    decomposer = StoryDecomposer(gcp_client, cfg)
    episode.scenes = decomposer.decompose(story_text, episode.characters)
    save_state(storage, episode, state_file)
    logger.info("Saved state after decomposition.")
    
    prompt_writer = PromptWriter(cfg)
    episode.scenes = prompt_writer.write_prompts(episode.scenes, episode.characters)
    save_state(storage, episode, state_file)
    
    kf_gen = KeyframeGenerator(gcp_client, cfg, character_refs=char_refs)
    for scene in episode.scenes:
        for shot in scene.shots:
            kf_gen.generate_pair(shot)
            save_state(storage, episode, state_file)
    
    logger.info("Keyframe generation complete! Review in the Storyboard, then click 'Approve & Generate Video'.")

@cli.command()
@click.option("--config", required=True, help="Path to episode config YAML")
def resume(config: str):
    """Resume pipeline: generate videos for approved keyframes and stitch."""
    logger.info("Resuming pipeline — video generation + stitching")
    cfg = load_config(config)
    gcp_client = GCPClient(cfg)
    storage = StorageManager(cfg)
    state_file = cfg.get("pipeline", {}).get("state_file", "output/pipeline_state.json")
    
    try:
        episode = load_state(storage, state_file)
    except FileNotFoundError:
        logger.error("No pipeline state found. Run the full pipeline first.")
        return
    
    # Generate videos only for shots that have keyframes but no clips
    vid_gen = VideoGenerator(gcp_client, cfg)
    for scene in episode.scenes:
        for shot in scene.shots:
            if shot.keyframe_path and not shot.clip_path:
                logger.info(f"Generating video for approved shot {shot.id}...")
                vid_gen.generate_from_keyframe(shot)
                save_state(storage, episode, state_file)
            elif shot.clip_path:
                logger.info(f"Shot {shot.id} already has a clip, skipping.")
    
    # Stitch final video
    stitcher = Stitcher(cfg)
    final_video = stitcher.assemble(episode)
    if final_video:
        save_state(storage, episode, state_file)
        logger.info(f"Resume complete! Output: {final_video}")
    else:
        logger.error("Stitching failed.")

if __name__ == "__main__":
    cli()
