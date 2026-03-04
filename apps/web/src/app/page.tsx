'use client';

import { useState, useRef, useEffect } from 'react';
import { Sparkles, Wand2, UploadCloud, X, FileImage, FileVideo, Youtube, Save, Trash2, FolderOpen, Loader2, UserPlus, Users } from 'lucide-react';

interface Project {
  name: string;
  folder: string;
  episode_title: string;
  shot_count: number;
  saved_at: string;
}

interface CharacterRef {
  name: string;
  description: string;
  imagePath: string;
  fileName: string;
}

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [styleRefs, setStyleRefs] = useState<File[]>([]);
  const [youtubeUrls, setYoutubeUrls] = useState<string[]>([]);
  const [youtubeInput, setYoutubeInput] = useState("");
  const [story, setStory] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const charFileRef = useRef<HTMLInputElement>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectAction, setProjectAction] = useState("");

  // Character state
  const [characters, setCharacters] = useState<CharacterRef[]>([]);
  const [showCharDialog, setShowCharDialog] = useState(false);
  const [charName, setCharName] = useState("");
  const [charDesc, setCharDesc] = useState("");
  const [charFile, setCharFile] = useState<File | null>(null);
  const [charPreview, setCharPreview] = useState("");
  const [charUploading, setCharUploading] = useState(false);

  useEffect(() => { fetchProjects(); fetchCharacters(); }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch('/api/projects');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) { console.error(e); }
  };

  const fetchCharacters = async () => {
    try {
      const res = await fetch('/api/characters');
      const data = await res.json();
      setCharacters(data.characters || []);
    } catch (e) { console.error(e); }
  };

  const handleCharFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setCharFile(file);
      setCharPreview(URL.createObjectURL(file));
      setShowCharDialog(true);
    }
  };

  const handleCharUpload = async () => {
    if (!charFile || !charName.trim()) return;
    setCharUploading(true);
    try {
      const formData = new FormData();
      formData.append('name', charName.trim());
      formData.append('description', charDesc.trim());
      formData.append('image', charFile);
      const res = await fetch('/api/characters', { method: 'POST', body: formData });
      if ((await res.json()).success) {
        setShowCharDialog(false);
        setCharName(''); setCharDesc(''); setCharFile(null); setCharPreview('');
        fetchCharacters();
      }
    } catch (e) { console.error(e); }
    setCharUploading(false);
  };

  const handleCharDelete = async (name: string) => {
    if (!confirm(`Remove character "${name}"?`)) return;
    try {
      await fetch('/api/characters', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      fetchCharacters();
    } catch (e) { console.error(e); }
  };

  const handleSaveProject = async () => {
    if (!projectName.trim()) return;
    setProjectAction('saving');
    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName }),
      });
      if ((await res.json()).success) {
        setShowSaveDialog(false);
        setProjectName("");
        fetchProjects();
      }
    } catch (e) { console.error(e); }
    setProjectAction('');
  };

  const handleClearSession = async () => {
    if (!confirm('Clear the current session? All unsaved progress will be lost.')) return;
    setProjectAction('clearing');
    try {
      await fetch('/api/projects', { method: 'DELETE' });
      fetchProjects();
    } catch (e) { console.error(e); }
    setProjectAction('');
  };

  const handleLoadProject = async (folder: string) => {
    if (!confirm('Load this project? It will replace the current session.')) return;
    setProjectAction('loading');
    try {
      await fetch(`/api/projects/${folder}`, { method: 'POST' });
      fetchProjects();
    } catch (e) { console.error(e); }
    setProjectAction('');
  };

  const handleDeleteProject = async (folder: string) => {
    if (!confirm('Permanently delete this saved project?')) return;
    try {
      await fetch(`/api/projects/${folder}`, { method: 'DELETE' });
      fetchProjects();
    } catch (e) { console.error(e); }
  };

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

  const handleAddYoutubeUrl = () => {
    if (youtubeInput && (youtubeInput.includes("youtube.com") || youtubeInput.includes("youtu.be"))) {
      setYoutubeUrls(prev => [...prev, youtubeInput]);
      setYoutubeInput("");
    } else {
      alert("Please enter a valid YouTube URL");
    }
  };

  const removeYoutubeUrl = (idx: number) => {
    setYoutubeUrls(prev => prev.filter((_, i) => i !== idx));
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
      youtubeUrls.forEach((url) => formData.append("youtubeUrls", url));

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

        {/* Character References */}
        <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span className="flex h-8 w-8 rounded-full bg-primary/20 text-primary items-center justify-center text-sm">2</span>
              Characters
            </h2>
            <p className="text-sm text-muted-foreground pl-10">Upload reference images for each character. The AI will maintain their appearance across all shots.</p>
          </div>

          <div className="pl-10 space-y-4">
            <input
              type="file"
              ref={charFileRef}
              onChange={handleCharFileSelect}
              className="hidden"
              accept="image/*"
            />

            {characters.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {characters.map((c) => (
                  <div key={c.name} className="group relative rounded-xl border border-white/10 bg-black/40 overflow-hidden hover:border-primary/50 transition-all">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/api/asset?path=${encodeURIComponent(c.imagePath)}`}
                      alt={c.name}
                      className="w-full aspect-square object-cover"
                    />
                    <div className="p-3 space-y-1">
                      <p className="text-sm font-semibold text-white flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 text-primary" />
                        {c.name}
                      </p>
                      {c.description && <p className="text-xs text-white/50 line-clamp-2">{c.description}</p>}
                    </div>
                    <button
                      onClick={() => handleCharDelete(c.name)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 bg-black/70 hover:bg-red-500/80 text-white rounded-full p-1.5 transition-all"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => charFileRef.current?.click()}
              className="w-full rounded-xl border-2 border-dashed border-white/20 bg-black/30 hover:bg-black/50 p-6 flex flex-col items-center gap-2 transition-all text-white/40 hover:text-white cursor-pointer"
            >
              <UserPlus className="w-8 h-8" />
              <span className="text-sm font-medium">Add Character Reference</span>
              <span className="text-xs text-white/30">Upload an image, then name and describe the character</span>
            </button>
          </div>
        </div>

        {/* Character Labeling Dialog */}
        {showCharDialog && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => { setShowCharDialog(false); setCharFile(null); setCharPreview(''); }}>
            <div className="glass-card p-6 w-full max-w-md space-y-4 shadow-2xl" onClick={e => e.stopPropagation()}>
              <h3 className="text-lg font-semibold text-white">Who is this character?</h3>

              {charPreview && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={charPreview} alt="Preview" className="w-32 h-32 rounded-xl object-cover mx-auto border-2 border-primary/30" />
              )}

              <div className="space-y-3">
                <input
                  type="text"
                  value={charName}
                  onChange={e => setCharName(e.target.value)}
                  placeholder="Character name (e.g. Hana)"
                  className="w-full bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-white/30"
                  autoFocus
                />
                <textarea
                  value={charDesc}
                  onChange={e => setCharDesc(e.target.value)}
                  placeholder="Describe their appearance (e.g. ghostly girl with long cherry blossom pink hair, translucent skin, wearing a white kimono)"
                  className="w-full h-24 bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none transition-all placeholder:text-white/30"
                />
              </div>

              <div className="flex gap-3 justify-end">
                <button onClick={() => { setShowCharDialog(false); setCharFile(null); setCharPreview(''); }} className="px-4 py-2 text-sm text-white/70 hover:text-white transition-colors">Cancel</button>
                <button
                  onClick={handleCharUpload}
                  disabled={!charName.trim() || charUploading}
                  className="px-5 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {charUploading ? 'Saving...' : 'Save Character'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Aesthetic & Style (Multimodal) */}
        <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span className="flex h-8 w-8 rounded-full bg-primary/20 text-primary items-center justify-center text-sm">3</span>
              Visual Style References
            </h2>
            <p className="text-sm text-muted-foreground pl-10">Upload character art, moodboards, or video clips. Our AI will automatically extract the master style.</p>
          </div>

          <div className="pl-10 space-y-4">
            {/* YouTube Input */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Youtube className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  value={youtubeInput}
                  onChange={(e) => setYoutubeInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddYoutubeUrl()}
                  placeholder="Paste YouTube Video URL for style..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-white/30"
                />
              </div>
              <button
                onClick={handleAddYoutubeUrl}
                className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Add
              </button>
            </div>

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

            {(styleRefs.length > 0 || youtubeUrls.length > 0) && (
              <div className="flex flex-wrap gap-3 mt-4">
                {youtubeUrls.map((url, idx) => (
                  <div key={`yt-${idx}`} className="relative flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg py-2 px-3 pr-8">
                    <Youtube className="w-4 h-4 text-red-500" />
                    <span className="text-xs font-medium text-white/80 max-w-[150px] truncate">{url}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); removeYoutubeUrl(idx); }}
                      className="absolute right-2 text-white/40 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}

                {styleRefs.map((file, idx) => (
                  <div key={`file-${idx}`} className="relative flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg py-2 px-3 pr-8">
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
        <div className="pt-4 flex justify-end gap-3">
          <button
            onClick={handleClearSession}
            disabled={!!projectAction}
            className="inline-flex items-center gap-2 rounded-full border border-white/20 text-white/70 px-6 py-4 font-medium hover:bg-white/10 hover:text-white transition-all text-sm disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            Clear Session
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            disabled={!!projectAction}
            className="inline-flex items-center gap-2 rounded-full border border-primary/40 text-primary px-6 py-4 font-medium hover:bg-primary/10 transition-all text-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Save Project
          </button>
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

        {/* Save Dialog */}
        {showSaveDialog && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setShowSaveDialog(false)}>
            <div className="glass-card p-6 w-full max-w-md space-y-4 shadow-2xl" onClick={e => e.stopPropagation()}>
              <h3 className="text-lg font-semibold text-white">Save as Project</h3>
              <input
                type="text"
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSaveProject()}
                placeholder="Enter project name..."
                className="w-full bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-white/30"
                autoFocus
              />
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowSaveDialog(false)} className="px-4 py-2 text-sm text-white/70 hover:text-white transition-colors">Cancel</button>
                <button
                  onClick={handleSaveProject}
                  disabled={!projectName.trim() || projectAction === 'saving'}
                  className="px-5 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {projectAction === 'saving' ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Saved Projects */}
        {projects.length > 0 && (
          <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-primary" />
              Saved Projects
            </h2>
            <div className="space-y-2">
              {projects.map((p) => (
                <div key={p.folder} className="flex items-center justify-between p-4 rounded-xl bg-black/30 border border-white/10 hover:border-white/20 transition-colors">
                  <div className="space-y-1">
                    <p className="font-medium text-white text-sm">{p.name}</p>
                    <p className="text-xs text-white/50">{p.episode_title} · {p.shot_count} shots · saved {new Date(p.saved_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleLoadProject(p.folder)}
                      className="px-3 py-1.5 text-xs font-medium bg-white/10 hover:bg-white/20 text-white rounded-md transition-colors"
                    >
                      Load
                    </button>
                    <button
                      onClick={() => handleDeleteProject(p.folder)}
                      className="px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 rounded-md transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
