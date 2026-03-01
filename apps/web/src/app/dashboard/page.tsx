'use client';

import { Activity, CheckCircle2, Circle, Clock, Loader2, Play } from 'lucide-react';

const MOCK_JOBS = [
    {
        id: "run_7a9f_1",
        status: "generating_video",
        progress: 65,
        current_action: "Generating Video for scene_01_shot_003 (Veo 3.1)",
        shots: [
            { id: "shot_001", state: "done", type: "Keyframe & Video" },
            { id: "shot_002", state: "done", type: "Keyframe & Video" },
            { id: "shot_003", state: "active", type: "Video" },
            { id: "shot_004", state: "queued", type: "Keyframe" },
            { id: "shot_005", state: "queued", type: "Keyframe" },
        ]
    }
];

export default function Dashboard() {
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
                {MOCK_JOBS.map((job) => (
                    <div key={job.id} className="glass-card overflow-hidden">
                        {/* Job Header */}
                        <div className="p-6 border-b border-white/5 bg-black/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="space-y-1">
                                <div className="flex items-center gap-3">
                                    <h3 className="text-lg font-semibold tracking-tight text-white">Episode 1: The Last Starkeeper</h3>
                                    <span className="px-2.5 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-semibold animate-pulse tracking-wide uppercase">
                                        Running
                                    </span>
                                </div>
                                <p className="text-sm text-muted-foreground font-mono">{job.id}</p>
                            </div>

                            <div className="flex items-center gap-4 text-sm font-medium">
                                <div className="flex flex-col items-end">
                                    <span className="text-white/60">Overall Progress</span>
                                    <span className="text-2xl text-white font-bold">{job.progress}%</span>
                                </div>
                            </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="h-1.5 w-full bg-white/5">
                            <div
                                className="h-full bg-gradient-to-r from-primary/50 to-primary transition-all duration-1000 ease-out"
                                style={{ width: `${job.progress}%` }}
                            />
                        </div>

                        {/* Current Action Banner */}
                        <div className="px-6 py-4 bg-primary/5 border-b border-white/5 flex items-center gap-3">
                            <Loader2 className="w-5 h-5 text-primary animate-spin" />
                            <span className="text-sm font-medium text-white/90">{job.current_action}</span>
                        </div>

                        {/* Shots Grid */}
                        <div className="p-6">
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Shot Queue</h4>
                            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                                {job.shots.map((shot) => (
                                    <div
                                        key={shot.id}
                                        className={`p-4 rounded-xl border transition-colors ${shot.state === 'done' ? 'bg-white/5 border-white/10' :
                                                shot.state === 'active' ? 'bg-primary/10 border-primary/50 ring-1 ring-primary/20' :
                                                    'bg-transparent border-white/5'
                                            }`}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-sm font-semibold text-white/90">{shot.id}</span>
                                            {shot.state === 'done' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                                            {shot.state === 'active' && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
                                            {shot.state === 'queued' && <Circle className="w-4 h-4 text-white/20" />}
                                        </div>
                                        <p className="text-xs text-white/50 mb-3">{shot.type}</p>

                                        {shot.state === 'done' ? (
                                            <button className="w-full py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-medium rounded-md flex items-center justify-center gap-1 transition-colors">
                                                <Play className="w-3 h-3" /> Preview
                                            </button>
                                        ) : (
                                            <div className="w-full py-1.5 bg-black/20 text-white/30 text-xs font-medium rounded-md flex items-center justify-center">
                                                Waiting...
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
