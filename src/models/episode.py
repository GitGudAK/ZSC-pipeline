from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional

class Character(BaseModel):
    name: str
    description: str                    
    reference_images: List[str] = Field(default_factory=list)
    voice_id: Optional[str] = None      
    color_palette: List[str] = Field(default_factory=list)

class Shot(BaseModel):
    id: str                             
    scene_id: str
    order: int
    description: str                    
    shot_type: str                      
    camera_movement: str                
    duration_seconds: float             
    characters_present: List[str] = Field(default_factory=list)
    dialogue: Optional[str] = None      
    emotion: str                        
    location: str                       
    time_of_day: str                    
    transition_in: str                  
    transition_out: str                 
    image_prompt: Optional[str] = None  
    video_prompt: Optional[str] = None  
    keyframe_path: Optional[str] = None 
    keyframe_end_path: Optional[str] = None   # end frame keyframe
    clip_path: Optional[str] = None     
    audio_path: Optional[str] = None    
    status: str = "pending"             
    qa_score: Optional[float] = None    
    qa_notes: Optional[str] = None      
    image_prompt_end: Optional[str] = None    # end frame prompt

class Scene(BaseModel):
    id: str                             
    title: str
    summary: str
    location: str
    time_of_day: str
    mood: str
    characters: List[str] = Field(default_factory=list)
    shots: List[Shot] = Field(default_factory=list)

class Episode(BaseModel):
    title: str
    episode_number: int
    total_duration_target: float        
    synopsis: str
    characters: List[Character] = Field(default_factory=list)
    scenes: List[Scene] = Field(default_factory=list)
    style_guide: str                    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "decomposing"         
