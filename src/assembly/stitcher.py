import os
import logging
import subprocess
import shutil
from typing import List, Optional
from src.utils.storage import StorageManager
from src.models.episode import Shot, Scene, Episode

logger = logging.getLogger(__name__)


class Stitcher:
    """Assembles individual video clips into a final episode.
    
    Supports:
    - Simple concatenation (fast, no re-encoding)
    - Crossfade transitions between scenes (re-encodes, but higher quality)
    - Speed adjustment for clips that need to be slower
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.storage = StorageManager(config)
        self.local_tmp_dir = "/tmp/anime_pipeline_stitcher"
        os.makedirs(self.local_tmp_dir, exist_ok=True)
        
        # Assembly settings
        self.use_transitions = config.get("assembly", {}).get("use_transitions", True)
        self.crossfade_duration = config.get("assembly", {}).get("crossfade_seconds", 0.5)
        self.target_fps = config.get("episode", {}).get("fps", 24)
        self.resolution = config.get("episode", {}).get("resolution", "1080p")
        
    def _get_resolution_filter(self) -> str:
        """Get ffmpeg scale filter for target resolution."""
        res_map = {
            "720p": "1280:720",
            "1080p": "1920:1080",
            "4k": "3840:2160",
        }
        return res_map.get(self.resolution, "1920:1080")
    
    def _normalize_clip(self, input_path: str, output_path: str) -> bool:
        """Normalize a clip to consistent format/fps/resolution for concatenation."""
        scale = self._get_resolution_filter()
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale={scale}:force_original_aspect_ratio=decrease,"
                   f"pad={scale}:(ow-iw)/2:(oh-ih)/2:color=black,"
                   f"fps={self.target_fps}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"Normalize failed: {result.stderr[-300:]}")
                return False
            return True
        except Exception as e:
            logger.error(f"Normalize error: {e}")
            return False
        
    def assemble(self, episode: Episode) -> str:
        """Assemble all clips into a final episode video."""
        logger.info(f"Assembling episode '{episode.title}'...")
        
        # Gather all valid clips in scene/shot order
        clips = []
        scene_boundaries = set()  # Track where scene changes happen
        clip_idx = 0
        
        for scene in episode.scenes:
            scene_start = clip_idx
            for shot in scene.shots:
                if shot.clip_path:
                    clips.append({
                        "path": shot.clip_path,
                        "shot": shot,
                        "scene_boundary": clip_idx == scene_start and clip_idx > 0,
                    })
                    clip_idx += 1
                    
        if not clips:
            logger.error("No valid clips found for assembly.")
            return ""
            
        logger.info(f"Found {len(clips)} clips to assemble.")
        
        # Download and normalize all clips
        normalized_clips = []
        for idx, clip_info in enumerate(clips):
            local_raw = os.path.join(self.local_tmp_dir, f"raw_{idx}.mp4")
            local_norm = os.path.join(self.local_tmp_dir, f"norm_{idx}.mp4")
            
            # Download to local
            result_path = self.storage.download_to_local(clip_info["path"], local_raw)
            if result_path and result_path != local_raw:
                shutil.copy2(result_path, local_raw)
            
            if not os.path.exists(local_raw):
                logger.warning(f"Clip {idx} not found, skipping.")
                continue
            
            # Normalize
            if self._normalize_clip(local_raw, local_norm):
                normalized_clips.append({
                    "path": local_norm,
                    "scene_boundary": clip_info["scene_boundary"],
                })
            else:
                # Fallback: use raw clip
                normalized_clips.append({
                    "path": local_raw,
                    "scene_boundary": clip_info["scene_boundary"],
                })
        
        if not normalized_clips:
            logger.error("No clips survived normalization.")
            return ""
        
        # Concatenate with crossfades at scene boundaries
        local_output = os.path.join(self.local_tmp_dir, f"episode_{episode.episode_number}.mp4")
        
        if self.use_transitions and any(c["scene_boundary"] for c in normalized_clips):
            success = self._assemble_with_transitions(normalized_clips, local_output)
        else:
            success = self._assemble_concat(normalized_clips, local_output)
        
        if not success:
            logger.error("Assembly failed.")
            return ""
        
        # Upload final video
        final_dest = f"final/episode_{episode.episode_number}.mp4"
        final_path = self.storage.upload_from_local(local_output, final_dest)
        
        logger.info(f"Successfully assembled episode to {final_path}")
        return final_path
    
    def _assemble_concat(self, clips: List[dict], output_path: str) -> bool:
        """Simple concatenation using ffmpeg concat demuxer."""
        list_file = os.path.join(self.local_tmp_dir, "concat_list.txt")
        with open(list_file, "w") as f:
            for clip in clips:
                f.write(f"file '{os.path.abspath(clip['path'])}'\n")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"Concat failed: {result.stderr[-500:]}")
                return False
            return True
        except Exception as e:
            logger.error(f"Concat error: {e}")
            return False
    
    def _assemble_with_transitions(self, clips: List[dict], output_path: str) -> bool:
        """Concatenate with crossfade transitions at scene boundaries.
        
        Uses ffmpeg xfade filter for scene-change crossfades.
        Falls back to simple concat if filter graph gets too complex.
        """
        if len(clips) <= 1:
            return self._assemble_concat(clips, output_path)
        
        # For large numbers of clips, xfade chain gets unwieldy.
        # Strategy: concat clips within scenes, then xfade between scene chunks.
        # For simplicity, we'll do a two-pass approach:
        # Pass 1: concat within-scene clips
        # Pass 2: xfade between scene chunks
        
        scene_chunks = []
        current_chunk = [clips[0]]
        
        for clip in clips[1:]:
            if clip["scene_boundary"]:
                scene_chunks.append(current_chunk)
                current_chunk = [clip]
            else:
                current_chunk.append(clip)
        scene_chunks.append(current_chunk)
        
        # Pass 1: concat each scene chunk
        chunk_paths = []
        for i, chunk in enumerate(scene_chunks):
            if len(chunk) == 1:
                chunk_paths.append(chunk[0]["path"])
            else:
                chunk_output = os.path.join(self.local_tmp_dir, f"scene_chunk_{i}.mp4")
                if self._assemble_concat(chunk, chunk_output):
                    chunk_paths.append(chunk_output)
                else:
                    # Fallback: just use first clip
                    chunk_paths.append(chunk[0]["path"])
        
        if len(chunk_paths) == 1:
            shutil.copy2(chunk_paths[0], output_path)
            return True
        
        # Pass 2: xfade between scene chunks (limit to avoid filter complexity)
        if len(chunk_paths) > 10:
            logger.warning("Too many scene chunks for xfade, falling back to concat.")
            return self._assemble_concat(
                [{"path": p, "scene_boundary": False} for p in chunk_paths],
                output_path
            )
        
        # Build xfade filter chain
        inputs = []
        for p in chunk_paths:
            inputs.extend(["-i", p])
        
        # Get durations of each chunk for offset calculation
        offsets = []
        cumulative = 0.0
        fade_dur = self.crossfade_duration
        
        for i, path in enumerate(chunk_paths[:-1]):
            dur = self._get_duration(path)
            if dur is None:
                dur = 6.0  # fallback
            cumulative += dur - fade_dur
            offsets.append(cumulative)
        
        # Build xfade filter
        n = len(chunk_paths)
        filter_parts = []
        
        if n == 2:
            filter_parts.append(
                f"[0:v][1:v]xfade=transition=fade:duration={fade_dur}:offset={offsets[0]}[v]"
            )
            filter_complex = ";".join(filter_parts)
            map_label = "[v]"
        else:
            # Chain: [0][1] -> [v1], [v1][2] -> [v2], etc.
            filter_parts.append(
                f"[0:v][1:v]xfade=transition=fade:duration={fade_dur}:offset={offsets[0]}[v1]"
            )
            for i in range(2, n):
                prev = f"[v{i-1}]"
                next_label = f"[v{i}]" if i < n - 1 else "[v]"
                filter_parts.append(
                    f"{prev}[{i}:v]xfade=transition=fade:duration={fade_dur}:offset={offsets[i-1]}{next_label}"
                )
            filter_complex = ";".join(filter_parts)
            map_label = "[v]"
        
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", map_label,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.warning(f"Xfade failed, falling back to concat: {result.stderr[-300:]}")
                return self._assemble_concat(
                    [{"path": p, "scene_boundary": False} for p in chunk_paths],
                    output_path
                )
            return True
        except Exception as e:
            logger.error(f"Xfade error: {e}")
            return self._assemble_concat(
                [{"path": p, "scene_boundary": False} for p in chunk_paths],
                output_path
            )
    
    def _get_duration(self, path: str) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        return None
