import { NextResponse } from 'next/server';
import { writeFile, mkdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

import { PROJECT_ROOT, CHARACTERS_DIR, MANIFEST_PATH } from '@/lib/paths';

const CHARS_DIR = CHARACTERS_DIR;

// POST — Generate a character image from description + style guide
export async function POST(request: Request) {
    try {
        const { name, description } = await request.json();

        if (!name || !description) {
            return NextResponse.json({ error: 'Name and description are required' }, { status: 400 });
        }

        // Load style guide from config
        const { default: yaml } = await import('yaml');
        const { readFile: readFileSync } = await import('fs/promises');

        let styleGuide = '';
        const configPath = join(PROJECT_ROOT, 'config', 'default_config.yaml');
        if (existsSync(configPath)) {
            const raw = await readFileSync(configPath, 'utf-8');
            const cfg = yaml.parse(raw);
            styleGuide = cfg?.style?.guide || '';
        }

        // Build the generation prompt
        const prompt = [
            styleGuide ? `STYLE: ${styleGuide}` : '',
            `CHARACTER PORTRAIT: Full body character reference sheet of ${name}.`,
            `${description}`,
            'Clean background, character facing forward, full body visible, high detail, consistent lighting.',
            'This is a character reference image for animation production.'
        ].filter(Boolean).join('\n');

        // Call fal.ai to generate the character image
        const FAL_KEY = process.env.FAL_KEY;
        if (!FAL_KEY) {
            return NextResponse.json({ error: 'FAL_KEY not configured' }, { status: 500 });
        }

        const falResponse = await fetch('https://queue.fal.run/fal-ai/nano-banana-2', {
            method: 'POST',
            headers: {
                'Authorization': `Key ${FAL_KEY}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt }),
        });

        if (!falResponse.ok) {
            const err = await falResponse.text();
            console.error('fal.ai generation failed:', err);
            return NextResponse.json({ error: 'Image generation failed' }, { status: 500 });
        }

        const falResult = await falResponse.json();

        // Handle queue-based response
        let imageUrl: string | null = null;
        if (falResult.images?.[0]?.url) {
            imageUrl = falResult.images[0].url;
        } else if (falResult.request_id) {
            // Poll for result
            const requestId = falResult.request_id;
            for (let i = 0; i < 60; i++) {
                await new Promise(r => setTimeout(r, 2000));
                const statusRes = await fetch(`https://queue.fal.run/fal-ai/nano-banana-2/requests/${requestId}/status`, {
                    headers: { 'Authorization': `Key ${FAL_KEY}` },
                });
                const status = await statusRes.json();
                if (status.status === 'COMPLETED') {
                    const resultRes = await fetch(`https://queue.fal.run/fal-ai/nano-banana-2/requests/${requestId}`, {
                        headers: { 'Authorization': `Key ${FAL_KEY}` },
                    });
                    const result = await resultRes.json();
                    imageUrl = result.images?.[0]?.url;
                    break;
                }
            }
        }

        if (!imageUrl) {
            return NextResponse.json({ error: 'No image generated' }, { status: 500 });
        }

        // Download and save the image
        const imgRes = await fetch(imageUrl);
        const imgBuffer = Buffer.from(await imgRes.arrayBuffer());

        await mkdir(CHARS_DIR, { recursive: true });
        const safeName = name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
        const fileName = `${safeName}_${Date.now()}.jpg`;
        const imagePath = join(CHARS_DIR, fileName);
        await writeFile(imagePath, imgBuffer);

        // Update manifest
        let characters: any[] = [];
        if (existsSync(MANIFEST_PATH)) {
            try { characters = JSON.parse(await readFile(MANIFEST_PATH, 'utf-8')); } catch { }
        }

        // Remove existing with same name
        characters = characters.filter((c: any) => c.name.toLowerCase() !== name.toLowerCase());
        const entry = {
            name,
            description,
            imagePath: `./output/characters/${fileName}`,
            fileName,
        };
        characters.push(entry);
        await writeFile(MANIFEST_PATH, JSON.stringify(characters, null, 2));

        console.log(`Generated character: ${name} → ${imagePath}`);

        return NextResponse.json({ success: true, character: entry });
    } catch (error) {
        console.error('Character generation failed:', error);
        return NextResponse.json({ error: 'Failed to generate character' }, { status: 500 });
    }
}
