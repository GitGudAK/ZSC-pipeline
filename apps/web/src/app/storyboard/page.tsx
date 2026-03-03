'use client';

import { useState, useEffect } from 'react';
import { Camera, RefreshCw, Play, Film, MessageCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Storyboard() {
    const [selectedShot, setSelectedShot] = useState<string | null>(null);
    const [job, setJob] = useState<any>(null);

    useEffect(() => {
        const fetchPipeline = () => {
            fetch('/api/pipeline')
                .then(res => res.json())
                .then(data => setJob(data.state))
                .catch(err => console.error(err));
        };
        fetchPipeline(); // initial fetch
        const interval = setInterval(fetchPipeline, 3000);
        return () => clearInterval(interval);
    }, []);

    const shots = job?.scenes?.flatMap((scene: any) => scene.shots) || [];

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <header className="flex items-center justify-between pb-4 border-b border-white/10">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">Storyboard Editor</h1>
                    <p className="text-muted-foreground mt-1">Review and refine AI-generated shots before rendering.</p>
                </div>
                <div className="flex gap-3">
                    <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-medium transition-colors text-sm flex items-center gap-2">
                        <RefreshCw className="w-4 h-4" /> Regenerate All
                    </button>
                    <button className="px-5 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg font-medium transition-colors text-sm shadow-[0_0_20px_-5px_rgba(var(--primary),0.5)]">
                        Approve & Generate Video
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pt-4">
                {shots.map((shot: any, idx: number) => (
                    <div
                        key={shot.id}
                        onClick={() => setSelectedShot(shot.id)}
                        className={cn(
                            "group flex flex-col rounded-xl border border-white/10 bg-black/40 overflow-hidden cursor-pointer transition-all hover:bg-black/60 hover:border-primary/50",
                            selectedShot === shot.id && "ring-2 ring-primary border-transparent"
                        )}
                    >
                        {/* Thumbnail Area */}
                        <div className="relative aspect-video bg-white/5 border-b border-white/10 flex flex-col justify-end">
                            {shot.keyframe_path ? (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img src={`/api/asset?path=${encodeURIComponent(shot.keyframe_path)}`} alt={shot.description} className="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-white/20 group-hover:text-white/40">
                                    <Camera className="w-8 h-8" />
                                </div>
                            )}

                            {/* Badges */}
                            <div className="relative p-3 flex justify-between items-end bg-gradient-to-t from-black/80 to-transparent">
                                <span className="text-xs font-medium px-2 py-1 bg-black/60 backdrop-blur-md rounded text-white/90">
                                    Shot {idx + 1}
                                </span>
                                <span className="text-xs font-medium px-2 py-1 bg-black/60 backdrop-blur-md rounded text-primary-foreground flex items-center gap-1">
                                    <Play className="w-3 h-3" /> {shot.duration_seconds}s
                                </span>
                            </div>
                        </div>

                        {/* Details */}
                        <div className="p-4 space-y-3 flex-1">
                            <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider">
                                <Film className="w-3.5 h-3.5" />
                                {shot.shot_type} • {shot.camera_movement}
                            </div>

                            <p className="text-sm text-gray-300 line-clamp-3 leading-relaxed">
                                {shot.description}
                            </p>

                            {shot.dialogue && (
                                <div className="mt-auto pt-3 border-t border-white/10">
                                    <p className="text-xs text-gray-400 italic flex items-start gap-2">
                                        <MessageCircle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-white/40" />
                                        &quot;{shot.dialogue}&quot;
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Add New Shot Button */}
                <button className="flex flex-col rounded-xl border border-dashed border-white/20 bg-transparent hover:bg-white/5 items-center justify-center min-h-[300px] text-white/40 hover:text-white transition-colors gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
                        <span className="text-2xl font-light leading-none mb-1">+</span>
                    </div>
                    <span className="text-sm font-medium">Insert Shot</span>
                </button>
            </div>
        </div>
    );
}
