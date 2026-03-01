import os
import logging
import ffmpeg
from typing import List
from src.models.episode import Shot, Episode

logger = logging.getLogger(__name__)

class Stitcher:
    def __init__(self, config: dict):
        self.config = config
        self.output_dir = os.path.join(config.get("pipeline", {}).get("output_dir", "./output"), "final")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def assemble(self, episode: Episode) -> str:
        logger.info(f"Assembling episode {episode.title}...")
        
        # Gather all valid clips
        clips = []
        for scene in episode.scenes:
            for shot in scene.shots:
                if shot.clip_path and os.path.exists(shot.clip_path):
                    clips.append(shot.clip_path)
                    
        if not clips:
            logger.error("No valid clips found for assembly.")
            return ""
            
        output_file = os.path.join(self.output_dir, f"episode_{episode.episode_number}.mp4")
        
        try:
            list_file_path = os.path.join(self.output_dir, "concat_list.txt")
            with open(list_file_path, "w") as f:
                for clip in clips:
                    abs_path = os.path.abspath(clip)
                    f.write(f"file '{abs_path}'\\n")
                    
            logger.info(f"Running ffmpeg concatenation for {len(clips)} clips...")
            
            (
                ffmpeg
                .input(list_file_path, format='concat', safe=0)
                .output(output_file, c='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"Successfully assembled episode to {output_file}")
            return output_file
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            return ""
        except Exception as e:
            logger.error(f"Assembly failed: {e}")
            return ""
