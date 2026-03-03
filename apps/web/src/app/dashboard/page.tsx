'use client';

import { Activity, CheckCircle2, Circle, Clock, Loader2, Play } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function Dashboard() {
    const [job, setJob] = useState<any>(null);

    useEffect(() => {
        const interval = setInterval(() => {
            fetch('/api/pipeline')
                .then(res => res.json())
                .then(data => setJob(data.state))
                .catch(err => console.error(err));
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <header className="flex items-center justify-between pb-4 border-b border-white/10">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                        <Activity className="w-8 h-8 text-primary" />
                        Generation Queue
                    </h1>
                    <p className="text-muted-foreground mt-1">Monitor active pipeline executions running in Google Cloud.</p>
                </div>
            </header>

            <div className="space-y-6">
                {!job || !job.title ? (
                    <div className="glass-card p-12 text-center text-muted-foreground">
                        <Loader2 className="w-8 h-8 text-white/20 animate-spin mx-auto mb-4" />
                        <p>Waiting for pipeline execution...</p>
                    </div>
                ) : (
                    <div key={job.title} className="glass-card overflow-hidden">
                        {/* Job Header */}
                        <div className="p-6 border-b border-white/5 bg-black/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="space-y-1">
                                <div className="flex items-center gap-3">
                                    <h3 className="text-lg font-semibold tracking-tight text-white">Episode {job.episode_number}: {job.title}</h3>
                                    <span className="px-2.5 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-semibold animate-pulse tracking-wide uppercase">
                                        Running
                                    </span>
                                </div>
                                <p className="text-sm text-muted-foreground">{job.synopsis}</p>
                            </div>
                        </div>

                        {/* Progress Bar (Placeholder for real compute) */}
                        <div className="h-1.5 w-full bg-white/5">
                            <div className="h-full bg-gradient-to-r from-primary/50 to-primary w-full transition-all duration-1000 ease-out animate-pulse" />
                        </div>

                        {/* Master Style Guide Info Panel */}
                        {job.style_guide && (
                            <div className="px-6 py-5 border-b border-white/5 bg-black/40">
                                <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                                    <Activity className="w-4 h-4" />
                                    Extracted Master Style
                                </h4>
                                <p className="text-sm text-white/80 leading-relaxed italic border-l-2 border-primary/50 pl-4 py-1">
                                    &quot;{job.style_guide}&quot;
                                </p>
                            </div>
                        )}

                        {/* Shots Grid */}
                        <div className="p-6">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Shot Queue</h4>
                            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                                {job.scenes?.map((scene: any, s_idx: number) => (
                                    scene.shots?.map((shot: any, idx: number) => (
                                        <div
                                            key={`${s_idx}-${idx}`}
                                            className="p-4 rounded-xl border bg-white/5 border-white/10 transition-colors"
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-sm font-semibold text-white/90">Shot {idx + 1}</span>
                                                {shot.video_path ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <Loader2 className="w-4 h-4 text-primary animate-spin" />}
                                            </div>
                                            <p className="text-xs text-white/50 mb-3">{shot.visual_description?.substring(0, 40) || "Processing generation..."}...</p>

                                            {shot.video_path ? (
                                                <button className="w-full py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-medium rounded-md flex items-center justify-center gap-1 transition-colors">
                                                    <Play className="w-3 h-3" /> Preview
                                                </button>
                                            ) : shot.keyframe_path ? (
                                                <div className="w-full py-1.5 bg-primary/20 text-primary text-xs font-medium rounded-md flex items-center justify-center gap-1">
                                                    Generating Video...
                                                </div>
                                            ) : (
                                                <div className="w-full py-1.5 bg-black/20 text-white/30 text-xs font-medium rounded-md flex items-center justify-center gap-1">
                                                    Waiting...
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
