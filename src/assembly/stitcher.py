import os
import logging
import ffmpeg
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
                    # Download each clip to local temp dir
                    local_clip_path = os.path.join(self.local_tmp_dir, f"clip_{idx}.mp4")
                    self.storage.download_to_local(clip, local_clip_path)
                    
                    if os.path.exists(local_clip_path):
                        abs_path = os.path.abspath(local_clip_path)
                        f.write(f"file '{abs_path}'\\n")
                        
            logger.info(f"Running ffmpeg concatenation for {len(clips)} clips...")
            
            (
                ffmpeg
                .input(list_file_path, format='concat', safe=0)
                .output(local_output, c='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Upload final video back to storage
            final_path = self.storage.upload_from_local(local_output, final_cloud_dest)
            
            logger.info(f"Successfully assembled episode to {final_path}")
            return final_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            return ""
        except Exception as e:
            logger.error(f"Assembly failed: {e}")
            return ""
