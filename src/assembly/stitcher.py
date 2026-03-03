import os
import logging
import subprocess
from typing import List
from src.utils.storage import StorageManager
from src.models.episode import Shot, Episode

logger = logging.getLogger(__name__)

class Stitcher:
    def __init__(self, config: dict):
        self.config = config
        self.storage = StorageManager(config)
        self.local_tmp_dir = "/tmp/anime_pipeline_stitcher"
        os.makedirs(self.local_tmp_dir, exist_ok=True)
        
    def assemble(self, episode: Episode) -> str:
        logger.info(f"Assembling episode {episode.title}...")
        
        # Gather all valid clips
        clips = []
        for scene in episode.scenes:
            for shot in scene.shots:
                if shot.clip_path:
                    clips.append(shot.clip_path)
                    
        if not clips:
            logger.error("No valid clips found for assembly.")
            return ""
            
        final_cloud_dest = f"final/episode_{episode.episode_number}.mp4"
        local_output = os.path.join(self.local_tmp_dir, f"episode_{episode.episode_number}.mp4")
        
        try:
            list_file_path = os.path.join(self.local_tmp_dir, "concat_list.txt")
            with open(list_file_path, "w") as f:
                for idx, clip in enumerate(clips):
                    local_clip_path = os.path.join(self.local_tmp_dir, f"clip_{idx}.mp4")
                    
                    # download_to_local returns source for local files
                    result_path = self.storage.download_to_local(clip, local_clip_path)
                    
                    # If local, result_path is the original. Copy it to tmp for concat.
                    if result_path and result_path != local_clip_path:
                        import shutil
                        os.makedirs(os.path.dirname(local_clip_path), exist_ok=True)
                        shutil.copy2(result_path, local_clip_path)
                    
                    if os.path.exists(local_clip_path):
                        abs_path = os.path.abspath(local_clip_path)
                        f.write(f"file '{abs_path}'\n")
                        
            logger.info(f"Running ffmpeg concatenation for {len(clips)} clips...")
            
            # Use subprocess directly to avoid pipe deadlock from ffmpeg-python
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                local_output
            ]
            
            stderr_log = os.path.join(self.local_tmp_dir, "ffmpeg_stderr.log")
            with open(stderr_log, "w") as stderr_file:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    timeout=300  # 5 minute timeout
                )
            
            if result.returncode != 0:
                with open(stderr_log) as f:
                    err_text = f.read()[-500:]
                logger.error(f"FFmpeg error: {err_text}")
                return ""
            
            # Upload final video back to storage
            final_path = self.storage.upload_from_local(local_output, final_cloud_dest)
            
            logger.info(f"Successfully assembled episode to {final_path}")
            return final_path
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg concat timed out after 300s")
            return ""
        except Exception as e:
            logger.error(f"Assembly failed: {e}")
            return ""
