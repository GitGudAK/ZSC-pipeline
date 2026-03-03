import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { resolve } from 'path';

const PROJECT_ROOT = '/Users/ashwink/Desktop/ZSC-pipeline';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const pathParam = searchParams.get('path');

    if (!pathParam) {
        return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
    }

    try {
        // Resolve the path relative to the project root
        let absolutePath: string;
        if (pathParam.startsWith('/')) {
            absolutePath = pathParam;
        } else if (pathParam.startsWith('./')) {
            absolutePath = resolve(PROJECT_ROOT, pathParam);
        } else {
            absolutePath = resolve(PROJECT_ROOT, pathParam);
        }

        // Security: only allow serving from the project's output directory
        const outputDir = resolve(PROJECT_ROOT, 'output');
        if (!absolutePath.startsWith(outputDir)) {
            return NextResponse.json({ error: "Access denied" }, { status: 403 });
        }

        if (!existsSync(absolutePath)) {
            return NextResponse.json({ error: `File not found: ${absolutePath}` }, { status: 404 });
        }

        const data = await readFile(absolutePath);

        // Determine content type
        let contentType = 'application/octet-stream';
        if (absolutePath.endsWith('.jpg') || absolutePath.endsWith('.jpeg')) {
            contentType = 'image/jpeg';
        } else if (absolutePath.endsWith('.png')) {
            contentType = 'image/png';
        } else if (absolutePath.endsWith('.webp')) {
            contentType = 'image/webp';
        } else if (absolutePath.endsWith('.mp4')) {
            contentType = 'video/mp4';
        }

        return new NextResponse(data, {
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'no-cache',
            }
        });
    } catch (error) {
        console.error("Error serving asset:", error);
        return NextResponse.json({ error: "Internal server error" }, { status: 500 });
    }
}
