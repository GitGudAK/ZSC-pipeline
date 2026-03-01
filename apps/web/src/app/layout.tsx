import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from 'next/link';
import { Film, LayoutDashboard, Settings, Video } from 'lucide-react';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ZSC Anime Pipeline",
  description: "AI-powered anime production pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-background antialiased flex selection:bg-primary/30`}>
        {/* Sidebar */}
        <aside className="w-64 border-r border-border/50 bg-background/50 backdrop-blur-3xl flex-shrink-0 relative overflow-hidden hidden md:flex flex-col">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-[100px] -z-10 pointer-events-none" />

          <div className="h-16 flex items-center px-6 border-b border-white/5">
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent flex items-center gap-2">
              <Film className="w-5 h-5 text-primary" />
              ZSC Pipeline
            </span>
          </div>

          <div className="flex-1 py-6 px-4 space-y-2">
            <div className="px-2 pb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Studio
            </div>
            <Link href="/" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-foreground bg-primary/10 hover:bg-primary/20 transition-colors">
              <LayoutDashboard className="w-4 h-4 text-primary" />
              Project Setup
            </Link>
            <Link href="/storyboard" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
              <Film className="w-4 h-4" />
              Storyboard
            </Link>
            <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
              <Video className="w-4 h-4" />
              Generation Queue
            </Link>
          </div>

          <div className="p-4 border-t border-white/5">
            <button className="flex items-center gap-3 px-3 py-2 w-full text-sm font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors">
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-background via-background to-black border-l border-white/5 z-0 relative">
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay pointer-events-none" />
          <div className="flex-1 overflow-auto p-8 relative z-10 text-white">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
