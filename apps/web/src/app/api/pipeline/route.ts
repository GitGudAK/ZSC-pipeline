import { NextResponse } from 'next/server';
import { writeFile, mkdir, readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { exec } from 'child_process';

const PIPELINE_STATE_FILE = '/Users/ashwink/Desktop/ZSC-pipeline/output/pipeline_state.json';

export async function POST(request: Request) {
    try {
        const formData = await request.formData();
        const story = formData.get('story_text') as string;
        const styleRefFiles = formData.getAll('styleRefs') as File[];
        const youtubeUrls = formData.getAll('youtube_url') as string[];

        // Create a temp directory for the references
        const tmpDir = '/tmp/anime_style_refs';
        if (!existsSync(tmpDir)) {
            await mkdir(tmpDir, { recursive: true });
        }

        const allRefs: string[] = [...youtubeUrls];

        // Save all uploaded files to disk
        for (const file of styleRefFiles) {
            if (typeof file === 'object' && 'arrayBuffer' in file) {
                const bytes = await file.arrayBuffer();
                const buffer = Buffer.from(bytes);
                const filePath = join(tmpDir, `${Date.now()}_${file.name.replace(/\\s+/g, '_')}`);
                await writeFile(filePath, buffer);
                allRefs.push(filePath);
                console.log(`Saved style reference: ${filePath}`);
            }
        }

        const styleRefsArg = allRefs.length > 0 ? `--style-refs "${allRefs.join(",")}"` : "";

        // Save the story text
        const storyFilePath = join(tmpDir, `story_${Date.now()}.txt`);
        await writeFile(storyFilePath, Buffer.from(story));

        console.log(`Triggering pipeline for story...`);

        // Execute the CLI in the background
        const cmd = `cd /Users/ashwink/Desktop/ZSC-pipeline && export GCP_PROJECT_ID=gen-lang-client-0655380841 && source .venv/bin/activate || true && python -m src.main run --config config/example_episode.yaml --story ${storyFilePath} ${styleRefsArg} > /tmp/pipeline_run.log 2>&1 &`;

        exec(cmd, (error, stdout, stderr) => {
            if (error) console.error("CLI exec error", error);
        });

        return NextResponse.json({
            success: true,
            jobId: `run_${Math.random().toString(36).substring(7)}`,
            message: "Pipeline triggered successfully"
        });

    } catch (error) {
        console.error("Pipeline trigger failed:", error);
        return NextResponse.json(
            { success: false, error: "Failed to process trigger request" },
            { status: 500 }
        );
    }
}

export async function GET() {
    try {
        if (!existsSync(PIPELINE_STATE_FILE)) {
            return NextResponse.json({ status: "healthy", state: null, message: "No active pipeline state found" });
        }

        const data = await readFile(PIPELINE_STATE_FILE, 'utf-8');
        return NextResponse.json({
            status: "healthy",
            state: JSON.parse(data)
        });
    } catch (error) {
        console.error("Error reading pipeline state:", error);
        return NextResponse.json({ status: "error", state: null }, { status: 500 });
    }
}

