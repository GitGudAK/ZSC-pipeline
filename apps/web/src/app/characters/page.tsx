'use client';

import { useState, useEffect, useRef } from 'react';
import { Users, Sparkles, Trash2, Upload, Loader2, X } from 'lucide-react';

interface CharacterRef {
    name: string;
    description: string;
    imagePath: string;
    fileName: string;
}

export default function Characters() {
    const [characters, setCharacters] = useState<CharacterRef[]>([]);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Upload states
    const [uploadName, setUploadName] = useState('');
    const [uploadDesc, setUploadDesc] = useState('');
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadPreview, setUploadPreview] = useState('');
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => { fetchCharacters(); }, []);

    const fetchCharacters = async () => {
        try {
            const res = await fetch('/api/characters');
            const data = await res.json();
            setCharacters(data.characters || []);
        } catch (e) { console.error(e); }
    };

    const handleGenerate = async () => {
        if (!name.trim() || !description.trim()) return;
        setIsGenerating(true);
        setError('');
        try {
            const res = await fetch('/api/characters/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), description: description.trim() }),
            });
            const data = await res.json();
            if (data.success) {
                setName('');
                setDescription('');
                fetchCharacters();
            } else {
                setError(data.error || 'Generation failed');
            }
        } catch (e) {
            console.error(e);
            setError('Failed to generate character');
        }
        setIsGenerating(false);
    };

    const handleDelete = async (charName: string) => {
        if (!confirm(`Remove character "${charName}"?`)) return;
        try {
            await fetch('/api/characters', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: charName }),
            });
            fetchCharacters();
        } catch (e) { console.error(e); }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file && file.type.startsWith('image/')) {
            setUploadFile(file);
            setUploadPreview(URL.createObjectURL(file));
            setShowUploadDialog(true);
        }
    };

    const handleUpload = async () => {
        if (!uploadFile || !uploadName.trim()) return;
        setIsUploading(true);
        try {
            const formData = new FormData();
            formData.append('name', uploadName.trim());
            formData.append('description', uploadDesc.trim());
            formData.append('image', uploadFile);
            const res = await fetch('/api/characters', { method: 'POST', body: formData });
            if ((await res.json()).success) {
                setShowUploadDialog(false);
                setUploadName(''); setUploadDesc(''); setUploadFile(null); setUploadPreview('');
                fetchCharacters();
            }
        } catch (e) { console.error(e); }
        setIsUploading(false);
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            <header className="pb-4 border-b border-white/10">
                <h1 className="text-3xl font-bold tracking-tight text-white">Character Creator</h1>
                <p className="text-muted-foreground mt-1">Create and manage characters for your episode. Generate from description or upload reference images.</p>
            </header>

            {/* Generate Character */}
            <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
                <h2 className="text-lg font-semibold flex items-center gap-2 text-white">
                    <Sparkles className="w-5 h-5 text-primary" />
                    Generate from Description
                </h2>
                <p className="text-sm text-white/50">Describe a character and the AI will generate a reference image using your episode&apos;s style guide.</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input
                        type="text"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        placeholder="Character name (e.g. Hana)"
                        className="bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-white/30"
                    />
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Describe their appearance in detail (e.g. ghostly girl with cherry blossom pink hair, pale translucent skin, wearing a flowing white kimono with sakura petals embroidered on the sleeves)"
                        className="bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none transition-all placeholder:text-white/30 md:col-span-2 h-24"
                    />
                </div>

                {error && <p className="text-xs text-red-400">{error}</p>}

                <div className="flex gap-3">
                    <button
                        onClick={handleGenerate}
                        disabled={!name.trim() || !description.trim() || isGenerating}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        {isGenerating ? (
                            <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
                        ) : (
                            <><Sparkles className="w-4 h-4" /> Generate Character</>
                        )}
                    </button>

                    <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" accept="image/*" />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="inline-flex items-center gap-2 px-5 py-2.5 border border-white/20 hover:bg-white/5 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        <Upload className="w-4 h-4" /> Upload Instead
                    </button>
                </div>
            </div>

            {/* Upload Labeling Dialog */}
            {showUploadDialog && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => { setShowUploadDialog(false); setUploadFile(null); setUploadPreview(''); }}>
                    <div className="glass-card p-6 w-full max-w-md space-y-4 shadow-2xl" onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-semibold text-white">Who is this character?</h3>
                        {uploadPreview && (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img src={uploadPreview} alt="Preview" className="w-32 h-32 rounded-xl object-cover mx-auto border-2 border-primary/30" />
                        )}
                        <div className="space-y-3">
                            <input type="text" value={uploadName} onChange={e => setUploadName(e.target.value)} placeholder="Character name" className="w-full bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-white/30" autoFocus />
                            <textarea value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} placeholder="Describe their appearance" className="w-full h-24 bg-black/50 border border-white/10 rounded-lg py-2.5 px-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none transition-all placeholder:text-white/30" />
                        </div>
                        <div className="flex gap-3 justify-end">
                            <button onClick={() => { setShowUploadDialog(false); setUploadFile(null); setUploadPreview(''); }} className="px-4 py-2 text-sm text-white/70 hover:text-white transition-colors">Cancel</button>
                            <button onClick={handleUpload} disabled={!uploadName.trim() || isUploading} className="px-5 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                                {isUploading ? 'Saving...' : 'Save Character'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Character Grid */}
            {characters.length > 0 ? (
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2 text-white">
                        <Users className="w-5 h-5 text-primary" />
                        Your Characters ({characters.length})
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                        {characters.map(c => (
                            <div key={c.name} className="group relative rounded-xl border border-white/10 bg-black/40 overflow-hidden hover:border-primary/50 transition-all">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                    src={`/api/asset?path=${encodeURIComponent(c.imagePath)}`}
                                    alt={c.name}
                                    className="w-full aspect-[3/4] object-cover"
                                />
                                <div className="p-4 space-y-1">
                                    <p className="text-sm font-semibold text-white">{c.name}</p>
                                    {c.description && <p className="text-xs text-white/50 line-clamp-3">{c.description}</p>}
                                </div>
                                <button
                                    onClick={() => handleDelete(c.name)}
                                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 bg-black/70 hover:bg-red-500/80 text-white rounded-full p-2 transition-all"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div className="text-center py-16 text-white/30">
                    <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">No characters yet. Generate or upload your first character above.</p>
                </div>
            )}
        </div>
    );
}
