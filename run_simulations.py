#!/usr/bin/env python3
"""
Simulation runner: runs 3 end-to-end pipeline executions sequentially.
Each produces a ~2 minute final video using real API calls (Gemini + fal.ai).
"""
import os
import sys
import json
import shutil
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sim_runner")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
PROJECTS_DIR = os.path.join(PROJECT_ROOT, "projects")

SIMULATIONS = [
    {
        "name": "Neon Ronin",
        "story": "stories/sim_01_neon_ronin.txt",
        "config": "config/sim_episode.yaml",
    },
    {
        "name": "The Sky Garden",
        "story": "stories/sim_02_sky_garden.txt",
        "config": "config/sim_episode.yaml",
    },
    {
        "name": "The Last Train",
        "story": "stories/sim_03_last_train.txt",
        "config": "config/sim_episode.yaml",
    },
]


def clear_output():
    """Clear the output directory for a fresh run."""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info("Cleared output directory.")


def save_project(name: str, folder_name: str):
    """Save the current output as a named project."""
    project_dir = os.path.join(PROJECTS_DIR, folder_name)
    os.makedirs(project_dir, exist_ok=True)
    
    # Copy output
    saved_output = os.path.join(project_dir, "output")
    if os.path.exists(saved_output):
        shutil.rmtree(saved_output)
    shutil.copytree(OUTPUT_DIR, saved_output)
    
    # Read state for metadata
    state_file = os.path.join(OUTPUT_DIR, "pipeline_state.json")
    episode_title = "Unknown"
    shot_count = 0
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
            episode_title = state.get("title", "Unknown")
            shot_count = sum(len(s.get("shots", [])) for s in state.get("scenes", []))
    
    # Write metadata
    meta = {
        "name": name,
        "folder": folder_name,
        "episode_title": episode_title,
        "shot_count": shot_count,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(project_dir, "project_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    logger.info(f"Saved project '{name}' with {shot_count} shots to {project_dir}")


def run_pipeline(sim: dict, run_number: int) -> bool:
    """Run a single pipeline execution."""
    logger.info(f"\n{'='*60}")
    logger.info(f"SIMULATION {run_number}/3: {sim['name']}")
    logger.info(f"{'='*60}")
    
    clear_output()
    
    story_path = os.path.join(PROJECT_ROOT, sim["story"])
    config_path = os.path.join(PROJECT_ROOT, sim["config"])
    log_path = f"/tmp/sim_run_{run_number}.log"
    
    cmd = [
        sys.executable, "-m", "src.main", "run",
        "--config", config_path,
        "--story", story_path,
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"Log: {log_path}")
    
    start_time = time.time()
    
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env={**os.environ},
        )
        
        # Monitor progress
        while process.poll() is None:
            time.sleep(10)
            elapsed = int(time.time() - start_time)
            
            # Check state file for progress
            state_file = os.path.join(OUTPUT_DIR, "pipeline_state.json")
            status_msg = "waiting..."
            if os.path.exists(state_file):
                try:
                    with open(state_file) as f:
                        state = json.load(f)
                    scenes = state.get("scenes", [])
                    total_shots = sum(len(s.get("shots", [])) for s in scenes)
                    kf_done = sum(
                        1 for s in scenes for shot in s.get("shots", [])
                        if shot.get("keyframe_path")
                    )
                    vid_done = sum(
                        1 for s in scenes for shot in s.get("shots", [])
                        if shot.get("clip_path")
                    )
                    status_msg = f"shots={total_shots}, keyframes={kf_done}/{total_shots}, videos={vid_done}/{total_shots}"
                except Exception:
                    pass
            
            logger.info(f"  [{elapsed}s] {status_msg}")
        
        exit_code = process.returncode
    
    elapsed = int(time.time() - start_time)
    
    if exit_code != 0:
        logger.error(f"Pipeline failed with exit code {exit_code} after {elapsed}s")
        logger.error(f"Check log: {log_path}")
        # Print last 30 lines of log
        with open(log_path) as f:
            lines = f.readlines()
            logger.error("Last 30 lines of log:")
            for line in lines[-30:]:
                logger.error(f"  {line.rstrip()}")
        return False
    
    logger.info(f"Pipeline completed in {elapsed}s")
    
    # Check for final video
    final_dir = os.path.join(OUTPUT_DIR, "final")
    if os.path.exists(final_dir):
        videos = [f for f in os.listdir(final_dir) if f.endswith(".mp4")]
        if videos:
            video_path = os.path.join(final_dir, videos[0])
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"✅ Final video: {video_path} ({size_mb:.1f} MB)")
        else:
            logger.warning("⚠️ No final video found in output/final/")
    else:
        logger.warning("⚠️ output/final/ directory not found")
    
    # Save as project
    folder_name = f"sim_{run_number:02d}_{sim['name'].lower().replace(' ', '_')}"
    save_project(sim["name"], folder_name)
    
    return True


def main():
    logger.info("Starting 3 simulation runs...")
    logger.info(f"Project root: {PROJECT_ROOT}")
    
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    
    results = []
    for i, sim in enumerate(SIMULATIONS, 1):
        success = run_pipeline(sim, i)
        results.append((sim["name"], success))
        
        if not success:
            logger.error(f"Simulation {i} failed. Continuing to next...")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SIMULATION RESULTS")
    logger.info(f"{'='*60}")
    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {status}: {name}")
    
    # List all final videos
    for i, sim in enumerate(SIMULATIONS, 1):
        folder_name = f"sim_{i:02d}_{sim['name'].lower().replace(' ', '_')}"
        video_path = os.path.join(PROJECTS_DIR, folder_name, "output", "final", "episode_1.mp4")
        if os.path.exists(video_path):
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"  📹 {video_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
