import { NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

export async function POST(request: Request) {
    try {
        const formData = await request.formData();
        const story = formData.get('story') as string;
        const styleRefFiles = formData.getAll('styleRefs') as File[];

        // Create a temp directory for the references
        const tmpDir = '/tmp/anime_style_refs';
        if (!existsSync(tmpDir)) {
            await mkdir(tmpDir, { recursive: true });
        }

        const savedPaths: string[] = [];

        // Save all uploaded files to disk
        for (const file of styleRefFiles) {
            if (typeof file === 'object' && 'arrayBuffer' in file) {
                const bytes = await file.arrayBuffer();
                const buffer = Buffer.from(bytes);
                const filePath = join(tmpDir, `${Date.now()}_${file.name.replace(/\\s+/g, '_')}`);
                await writeFile(filePath, buffer);
                savedPaths.push(filePath);
                console.log(`Saved style reference: ${filePath}`);
            }
        }

        const styleRefsArg = savedPaths.join(",");

        // In a real implementation, this would:
        // Trigger the Cloud Run Job via Google Cloud SDK with the `--style-refs` arguments
        // Or execute the CLI locally:
        // exec(`python -m src.main run --config config/default_config.yaml --story ${story_temp_path} --style-refs ${styleRefsArg}`)

        console.log(`Mock triggering pipeline for story: ${story?.substring(0, 50)}...`);
        if (savedPaths.length > 0) {
            console.log(`With style references: ${styleRefsArg}`);
        }

        return NextResponse.json({
            success: true,
            jobId: `run_${Math.random().toString(36).substring(7)}`,
            savedPaths,
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
    // Polls the pipeline_state.json from GCS/local
    return NextResponse.json({
        status: "healthy",
        message: "Pipeline API is running"
    });
}
