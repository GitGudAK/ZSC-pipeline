'use client';

import { useState, useEffect } from 'react';
import { Camera, RefreshCw, Play, Film, MessageCircle, Loader2, CheckCircle2, Download, X, ArrowRight, Users } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Storyboard() {
    const [selectedShot, setSelectedShot] = useState<string | null>(null);
    const [viewingShot, setViewingShot] = useState<any>(null);
    const [job, setJob] = useState<any>(null);
    const [isApproving, setIsApproving] = useState(false);
    const [approveMessage, setApproveMessage] = useState('');

    useEffect(() => {
        const fetchPipeline = () => {
            fetch('/api/pipeline')
                .then(res => res.json())
                .then(data => setJob(data.state))
                .catch(err => console.error(err));
        };
        fetchPipeline();
        const interval = setInterval(fetchPipeline, 3000);
        return () => clearInterval(interval);
    }, []);

    const shots = job?.scenes?.flatMap((scene: any) => scene.shots) || [];

    const hasApprovedKeyframes = shots.some((s: any) => s.keyframe_path && !s.clip_path);
    const allHaveClips = shots.length > 0 && shots.every((s: any) => s.clip_path);

    const handleApproveAndGenerate = async () => {
        setIsApproving(true);
        setApproveMessage('');
        try {
            const res = await fetch('/api/pipeline/approve', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                setApproveMessage('Video generation started! Check the Generation Queue for progress.');
            } else {
                setApproveMessage(data.error || 'Failed to start video generation.');
            }
        } catch (e) {
            console.error(e);
            setApproveMessage('Error triggering video generation.');
        }
        setIsApproving(false);
    };

    const openViewer = (shot: any, idx: number) => {
        setViewingShot({ ...shot, displayIdx: idx });
    };

    const navigateShot = (direction: number) => {
        if (!viewingShot) return;
        const currentIdx = viewingShot.displayIdx;
        const nextIdx = currentIdx + direction;
        if (nextIdx >= 0 && nextIdx < shots.length) {
            setViewingShot({ ...shots[nextIdx], displayIdx: nextIdx });
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <header className="flex items-center justify-between pb-4 border-b border-white/10">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">Storyboard Editor</h1>
                    <p className="text-muted-foreground mt-1">Review and refine AI-generated shots before rendering.</p>
                </div>
                <div className="flex gap-3 items-center">
                    {approveMessage && (
                        <span className="text-xs text-primary animate-fade-in">{approveMessage}</span>
                    )}
                    <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-medium transition-colors text-sm flex items-center gap-2">
                        <RefreshCw className="w-4 h-4" /> Regenerate All
                    </button>
                    <button
                        onClick={handleApproveAndGenerate}
                        disabled={isApproving || (!hasApprovedKeyframes && !shots.length)}
                        className={cn(
                            "px-5 py-2 rounded-lg font-medium transition-colors text-sm shadow-[0_0_20px_-5px_rgba(var(--primary),0.5)] flex items-center gap-2",
                            allHaveClips
                                ? "bg-green-600 hover:bg-green-700 text-white"
                                : "bg-primary hover:bg-primary/90 text-primary-foreground",
                            "disabled:opacity-50"
                        )}
                    >
                        {isApproving ? (
                            <><Loader2 className="w-4 h-4 animate-spin" /> Starting...</>
                        ) : allHaveClips ? (
                            <><CheckCircle2 className="w-4 h-4" /> Videos Complete</>
                        ) : (
                            <><Play className="w-4 h-4" /> Approve &amp; Generate Video</>
                        )}
                    </button>
                </div>
            </header>

            {/* Final Video Download Banner */}
            {allHaveClips && (
                <div className="glass-card p-5 flex items-center justify-between bg-gradient-to-r from-green-500/10 to-primary/10 border border-green-500/30">
                    <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                        <div>
                            <p className="text-sm font-semibold text-white">Your video is ready!</p>
                            <p className="text-xs text-white/60">All {shots.length} shots have been generated and stitched.</p>
                        </div>
                    </div>
                    <a
                        href="/api/asset?path=./output/final/episode_1.mp4&download=true"
                        download="episode_final.mp4"
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors text-sm shadow-lg shadow-green-600/30"
                    >
                        <Download className="w-4 h-4" />
                        Download Final Video
                    </a>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pt-4">
                {shots.map((shot: any, idx: number) => (
                    <div
                        key={shot.id}
                        onClick={() => openViewer(shot, idx)}
                        className={cn(
                            "group flex flex-col rounded-xl border border-white/10 bg-black/40 overflow-hidden cursor-pointer transition-all hover:bg-black/60 hover:border-primary/50",
                            selectedShot === shot.id && "ring-2 ring-primary border-transparent"
                        )}
                    >
                        {/* Thumbnail Area — Start + End Frames */}
                        <div className="relative aspect-video bg-white/5 border-b border-white/10 flex flex-col justify-end">
                            {shot.keyframe_path && shot.keyframe_end_path ? (
                                <div className="absolute inset-0 flex">
                                    <div className="relative w-1/2 border-r border-white/20">
                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img src={`/api/asset?path=${encodeURIComponent(shot.keyframe_path)}`} alt="Start" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                        <span className="absolute top-1.5 left-1.5 text-[10px] font-semibold px-1.5 py-0.5 bg-black/70 backdrop-blur-sm rounded text-white/80">Start</span>
                                    </div>
                                    <div className="relative w-1/2">
                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img src={`/api/asset?path=${encodeURIComponent(shot.keyframe_end_path)}`} alt="End" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                        <span className="absolute top-1.5 right-1.5 text-[10px] font-semibold px-1.5 py-0.5 bg-black/70 backdrop-blur-sm rounded text-white/80">End</span>
                                    </div>
                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <div className="w-6 h-6 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center">
                                            <Play className="w-3 h-3 text-white/80" />
                                        </div>
                                    </div>
                                </div>
                            ) : shot.keyframe_path ? (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img src={`/api/asset?path=${encodeURIComponent(shot.keyframe_path)}`} alt={shot.description} className="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-white/20 group-hover:text-white/40">
                                    <Camera className="w-8 h-8" />
                                </div>
                            )}

                            {shot.clip_path && (
                                <div className="absolute top-2 right-2 z-10">
                                    <span className="text-xs font-medium px-2 py-1 bg-green-500/90 backdrop-blur-md rounded text-white flex items-center gap-1">
                                        <CheckCircle2 className="w-3 h-3" /> Video Ready
                                    </span>
                                </div>
                            )}

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

                <button className="flex flex-col rounded-xl border border-dashed border-white/20 bg-transparent hover:bg-white/5 items-center justify-center min-h-[300px] text-white/40 hover:text-white transition-colors gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
                        <span className="text-2xl font-light leading-none mb-1">+</span>
                    </div>
                    <span className="text-sm font-medium">Insert Shot</span>
                </button>
            </div>

            {/* =================== KEYFRAME VIEWER LIGHTBOX =================== */}
            {viewingShot && (
                <div
                    className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-6"
                    onClick={() => setViewingShot(null)}
                >
                    <div
                        className="relative w-full max-w-5xl bg-[#0c0c14] border border-white/10 rounded-2xl overflow-hidden shadow-2xl shadow-black/80"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-bold px-3 py-1 bg-primary/20 text-primary rounded-full">
                                    Shot {viewingShot.displayIdx + 1} of {shots.length}
                                </span>
                                <span className="text-sm font-semibold text-white/80 uppercase tracking-wider">
                                    {viewingShot.shot_type} • {viewingShot.camera_movement}
                                </span>
                            </div>
                            <button onClick={() => setViewingShot(null)} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                                <X className="w-5 h-5 text-white/60" />
                            </button>
                        </div>

                        {/* Keyframe Pair — Large */}
                        <div className="flex items-stretch gap-0 bg-black">
                            {/* Start Frame */}
                            <div className="relative flex-1">
                                {viewingShot.keyframe_path ? (
                                    <>
                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img
                                            src={`/api/asset?path=${encodeURIComponent(viewingShot.keyframe_path)}`}
                                            alt="Start frame"
                                            className="w-full aspect-video object-contain bg-black"
                                        />
                                        <span className="absolute top-3 left-3 text-xs font-semibold px-2.5 py-1 bg-black/70 backdrop-blur-sm rounded-lg text-white/90 border border-white/10">
                                            Start Frame
                                        </span>
                                    </>
                                ) : (
                                    <div className="aspect-video flex items-center justify-center bg-white/5 text-white/20">
                                        <Camera className="w-10 h-10" />
                                    </div>
                                )}
                            </div>

                            {/* Arrow */}
                            {viewingShot.keyframe_end_path && (
                                <div className="flex items-center px-3 bg-black">
                                    <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
                                        <ArrowRight className="w-5 h-5 text-primary" />
                                    </div>
                                </div>
                            )}

                            {/* End Frame */}
                            {viewingShot.keyframe_end_path && (
                                <div className="relative flex-1">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src={`/api/asset?path=${encodeURIComponent(viewingShot.keyframe_end_path)}`}
                                        alt="End frame"
                                        className="w-full aspect-video object-contain bg-black"
                                    />
                                    <span className="absolute top-3 right-3 text-xs font-semibold px-2.5 py-1 bg-black/70 backdrop-blur-sm rounded-lg text-white/90 border border-white/10">
                                        End Frame
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* Shot Details */}
                        <div className="px-6 py-5 space-y-4 border-t border-white/10">
                            <p className="text-sm text-gray-200 leading-relaxed">{viewingShot.description}</p>

                            <div className="flex flex-wrap gap-3">
                                <span className="text-xs px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white/70">
                                    <Play className="w-3 h-3 inline mr-1.5 -mt-0.5" />{viewingShot.duration_seconds}s
                                </span>
                                <span className="text-xs px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white/70">
                                    📍 {viewingShot.location}
                                </span>
                                <span className="text-xs px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white/70">
                                    🕐 {viewingShot.time_of_day}
                                </span>
                                {viewingShot.emotion && (
                                    <span className="text-xs px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white/70">
                                        💫 {viewingShot.emotion}
                                    </span>
                                )}
                            </div>

                            {viewingShot.characters_present?.length > 0 && (
                                <div className="flex items-center gap-2 text-xs text-white/50">
                                    <Users className="w-3.5 h-3.5" />
                                    Characters: {viewingShot.characters_present.join(', ')}
                                </div>
                            )}

                            {viewingShot.dialogue && (
                                <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-3">
                                    <p className="text-sm text-gray-300 italic">
                                        <MessageCircle className="w-3.5 h-3.5 inline mr-2 -mt-0.5 text-white/40" />
                                        &quot;{viewingShot.dialogue}&quot;
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Navigation Footer */}
                        <div className="flex items-center justify-between px-6 py-3 border-t border-white/10 bg-white/[0.02]">
                            <button
                                onClick={() => navigateShot(-1)}
                                disabled={viewingShot.displayIdx === 0}
                                className="px-4 py-2 text-sm text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                ← Previous Shot
                            </button>
                            <button
                                onClick={() => navigateShot(1)}
                                disabled={viewingShot.displayIdx === shots.length - 1}
                                className="px-4 py-2 text-sm text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                Next Shot →
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

