'use client';

import { useState, useRef } from 'react';
import { Sparkles, Wand2, UploadCloud, X, FileImage, FileVideo } from 'lucide-react';

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [styleRefs, setStyleRefs] = useState<File[]>([]);
  const [story, setStory] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/') || f.type.startsWith('video/'));
      setStyleRefs(prev => [...prev, ...files]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(f => f.type.startsWith('image/') || f.type.startsWith('video/'));
      setStyleRefs(prev => [...prev, ...files]);
    }
  };

  const removeFile = (idx: number) => {
    setStyleRefs(prev => prev.filter((_, i) => i !== idx));
  };

  const handleBeginPipeline = async () => {
    if (!story) {
      alert("Please enter a story before generating.");
      return;
    }

    setIsGenerating(true);

    try {
      const formData = new FormData();
      formData.append("story", story);
      styleRefs.forEach((file) => formData.append("styleRefs", file));

      const res = await fetch("/api/pipeline", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (data.success) {
        // In a real app, redirect to dashboard here or start polling
        console.log("Pipeline Triggered:", data);
        setTimeout(() => setIsGenerating(false), 2000);
      } else {
        alert("Failed to trigger pipeline");
        setIsGenerating(false);
      }
    } catch (e) {
      console.error(e);
      alert("Error triggering pipeline");
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <header className="space-y-2">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl text-transparent bg-clip-text bg-gradient-to-br from-white to-white/60">
          Create New Episode
        </h1>
        <p className="text-muted-foreground text-lg">
          Configure your story, characters, and aesthetic to begin the generation pipeline.
        </p>
      </header>

      <div className="grid gap-8">
        {/* Story Configuration */}
        <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span className="flex h-8 w-8 rounded-full bg-primary/20 text-primary items-center justify-center text-sm">1</span>
              The Story
            </h2>
            <p className="text-sm text-muted-foreground pl-10">Paste your screenplay or prose here.</p>
          </div>

          <div className="pl-10">
            <textarea
              value={story}
              onChange={(e) => setStory(e.target.value)}
              className="w-full h-48 rounded-xl bg-black/50 border border-white/10 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none placeholder:text-muted-foreground/50 transition-all font-mono"
              placeholder="In a world where stars are dying, Hikari discovers a fading star in an alleyway..."
            />
          </div>
        </div>

        {/* Aesthetic & Style (Multimodal) */}
        <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span className="flex h-8 w-8 rounded-full bg-primary/20 text-primary items-center justify-center text-sm">2</span>
              Visual Style References
            </h2>
            <p className="text-sm text-muted-foreground pl-10">Upload character art, moodboards, or video clips. Our AI will automatically extract the master style.</p>
          </div>

          <div className="pl-10 space-y-4">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="w-full relative rounded-xl border-2 border-dashed border-white/20 bg-black/30 hover:bg-black/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all flex flex-col items-center justify-center p-8 group cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                className="hidden"
                multiple
                accept="image/*,video/*"
              />
              <UploadCloud className="w-10 h-10 text-white/30 group-hover:text-primary transition-colors mb-3" />
              <p className="text-sm font-medium text-white/80">Drag and drop images or videos here</p>
              <p className="text-xs text-white/40 mt-1">or click to browse from your computer</p>
            </div>

            {styleRefs.length > 0 && (
              <div className="flex flex-wrap gap-3 mt-4">
                {styleRefs.map((file, idx) => (
                  <div key={idx} className="relative flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg py-2 px-3 pr-8">
                    {file.type.startsWith('video') ? <FileVideo className="w-4 h-4 text-primary" /> : <FileImage className="w-4 h-4 text-blue-400" />}
                    <span className="text-xs font-medium text-white/80 max-w-[150px] truncate">{file.name}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                      className="absolute right-2 text-white/40 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Generate Button Area */}
        <div className="pt-4 flex justify-end">
          <button
            onClick={handleBeginPipeline}
            disabled={isGenerating || !story}
            className="group relative inline-flex items-center justify-center gap-2 rounded-full bg-white text-black px-8 py-4 font-semibold hover:bg-white/90 disabled:opacity-50 disabled:hover:scale-100 transition-all shadow-[0_0_40px_-10px_rgba(255,255,255,0.4)] hover:shadow-[0_0_60px_-15px_rgba(255,255,255,0.6)] hover:-translate-y-0.5"
          >
            {isGenerating ? (
              <>
                <div className="animate-spin h-5 w-5 border-2 border-black/20 border-t-black rounded-full" />
                Decomposing Story...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" />
                Begin Pipeline
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
