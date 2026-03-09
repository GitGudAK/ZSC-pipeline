"""Generate keyframe(s) for a single shot or all shots.

Usage:
  python -m src.generation.generate_single --config <config> --shot-id <id> [--prompt <prompt>] [--prompt-end <prompt>]
  python -m src.generation.generate_single --config <config> --all
"""
import os
import json
import logging
import click
import yaml

from src.utils.gcp_client import GCPClient
from src.generation.keyframe_gen import KeyframeGenerator
from src.models.episode import Episode
from src.utils.storage import StorageManager

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

    def replace_env_vars(d):
        for k, v in d.items():
            if isinstance(v, dict):
                replace_env_vars(v)
            elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                d[k] = os.environ.get(env_key, v)
    replace_env_vars(base_config)
    return base_config


def load_character_refs() -> dict:
    manifest_path = os.path.join("output", "characters", "manifest.json")
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r") as f:
            entries = json.load(f)
    except Exception:
        return {}
    char_refs = {}
    for entry in entries:
        name = entry.get("name", "")
        img_path = entry.get("imagePath", "")
        if img_path:
            char_refs[name.lower()] = img_path
    return char_refs


@click.command()
@click.option("--config", required=True, help="Config YAML path")
@click.option("--shot-id", default=None, help="Regenerate a single shot by ID")
@click.option("--prompt", default=None, help="Override start-frame prompt")
@click.option("--prompt-end", default=None, help="Override end-frame prompt")
@click.option("--image-model", default=None, help="Image model override: 'flux' or 'nano_banana_2'")
@click.option("--all", "gen_all", is_flag=True, help="Generate keyframes for ALL shots")
def main(config: str, shot_id: str, prompt: str, prompt_end: str, image_model: str, gen_all: bool):
    cfg = load_config(config)
    state_file = cfg.get("pipeline", {}).get("state_file", "output/pipeline_state.json")
    storage = StorageManager(cfg)

    # Load state
    data = storage.read_json(state_file)
    if not data:
        logger.error("No pipeline state found.")
        return
    episode = Episode.model_validate(data)

    gcp_client = GCPClient(cfg)
    char_refs = load_character_refs()
    kf_gen = KeyframeGenerator(gcp_client, cfg, character_refs=char_refs)

    if gen_all:
        # Generate for all shots that have prompts
        total = 0
        for scene in episode.scenes:
            for shot in scene.shots:
                if shot.image_prompt:
                    logger.info(f"Generating keyframes for {shot.id}...")
                    kf_gen.generate_pair(shot, model_override=image_model)
                    storage.write_json(episode.model_dump(mode='json'), state_file)
                    total += 1
        logger.info(f"Generated keyframes for {total} shots.")

    elif shot_id:
        # Find the specific shot
        target = None
        for scene in episode.scenes:
            for shot in scene.shots:
                if shot.id == shot_id:
                    target = shot
                    break
        if not target:
            logger.error(f"Shot {shot_id} not found.")
            return

        # Override prompts if provided
        if prompt:
            target.image_prompt = prompt
        if prompt_end:
            target.image_prompt_end = prompt_end

        logger.info(f"Regenerating keyframes for {shot_id} (model: {image_model or 'default'})...")
        kf_gen.generate_pair(target, model_override=image_model)
        storage.write_json(episode.model_dump(mode='json'), state_file)
        logger.info(f"Done. Keyframe saved for {shot_id}.")

    else:
        logger.error("Specify --shot-id <id> or --all")


if __name__ == "__main__":
    main()
