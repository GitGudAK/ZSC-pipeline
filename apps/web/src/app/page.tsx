'use client';

import { useState } from 'react';
import { Sparkles, Wand2 } from 'lucide-react';

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);

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
              className="w-full h-48 rounded-xl bg-black/50 border border-white/10 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none placeholder:text-muted-foreground/50 transition-all font-mono"
              placeholder="In a world where stars are dying, Hikari discovers a fading star in an alleyway..."
            />
          </div>
        </div>

        {/* Style Guide */}
        <div className="glass-card p-6 space-y-4 shadow-xl shadow-black/50">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span className="flex h-8 w-8 rounded-full bg-primary/20 text-primary items-center justify-center text-sm">2</span>
              Aesthetic & Style
            </h2>
            <p className="text-sm text-muted-foreground pl-10">Define the visual identity for the generated keyframes and video.</p>
          </div>

          <div className="pl-10">
            <textarea
              className="w-full h-24 rounded-xl bg-black/50 border border-white/10 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none placeholder:text-muted-foreground/50 transition-all"
              defaultValue="Modern anime style, vibrant colors, clean linework, expressive eyes, dynamic lighting. Similar to Makoto Shinkai's color palette with Studio Trigger's energy."
            />
          </div>
        </div>

        {/* Generate Button Area */}
        <div className="pt-4 flex justify-end">
          <button
            onClick={() => setIsGenerating(true)}
            className="group relative inline-flex items-center justify-center gap-2 rounded-full bg-white text-black px-8 py-4 font-semibold hover:bg-white/90 transition-all shadow-[0_0_40px_-10px_rgba(255,255,255,0.4)] hover:shadow-[0_0_60px_-15px_rgba(255,255,255,0.6)] hover:-translate-y-0.5"
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
