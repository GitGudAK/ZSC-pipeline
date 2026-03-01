import os
import sys
import logging
import argparse
from src.main import cli

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # In Cloud Run Jobs, we can pass args, but sometimes it's easier to read from ENV
    # Or we just let the Docker ENTRYPOINT run it.
    
    config_url = os.environ.get("CONFIG_URL", "config/example_episode.yaml")
    story_url = os.environ.get("STORY_URL", "test_story.txt")
    
    logger.info("==========================================")
    logger.info("   STARTING ANIME PIPELINE CLOUD JOB      ")
    logger.info("==========================================")
    
    # We essentially mock sys.argv to run the click CLI
    sys.argv = ["main.py", "run", "--config", config_url, "--story", story_url]
    
    try:
        cli()
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Pipeline executed successfully in Cloud Run.")
    sys.exit(0)
