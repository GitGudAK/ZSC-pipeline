import { NextResponse } from 'next/server';
import { readFile, readdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

const CHARACTERS_DIR = '/Users/ashwink/Desktop/ZSC-pipeline/output/characters';

export async function POST(request: Request) {
    try {
        const formData = await request.formData();
        const story = formData.get('story') as string;
        const styleRefFiles = formData.getAll('styleRefs') as File[];
        const youtubeUrls = formData.getAll('youtubeUrls') as string[];

        if (!story || story.trim().length < 50) {
            return NextResponse.json(
                { error: 'Story text is too short for analysis.' },
                { status: 400 }
            );
        }

        // Collect character images from manifest
        const charDescriptions: string[] = [];
        const charImageParts: Array<{ inlineData: { mimeType: string; data: string } }> = [];

        const manifestPath = join(CHARACTERS_DIR, 'manifest.json');
        if (existsSync(manifestPath)) {
            const manifest = JSON.parse(await readFile(manifestPath, 'utf-8'));
            for (const char of manifest) {
                charDescriptions.push(`${char.name}: ${char.description}`);
                const imgPath = char.imagePath?.startsWith('./')
                    ? join('/Users/ashwink/Desktop/ZSC-pipeline', char.imagePath.slice(2))
                    : char.imagePath;
                if (imgPath && existsSync(imgPath)) {
                    const imgBuf = await readFile(imgPath);
                    const ext = imgPath.split('.').pop()?.toLowerCase() || 'jpeg';
                    const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
                    charImageParts.push({
                        inlineData: { mimeType: mime, data: imgBuf.toString('base64') },
                    });
                }
            }
        }

        // Collect uploaded style reference images
        const styleImageParts: Array<{ inlineData: { mimeType: string; data: string } }> = [];
        for (const file of styleRefFiles) {
            if (typeof file === 'object' && 'arrayBuffer' in file && file.type.startsWith('image/')) {
                const bytes = await file.arrayBuffer();
                styleImageParts.push({
                    inlineData: { mimeType: file.type, data: Buffer.from(bytes).toString('base64') },
                });
            }
        }

        // Build youtube context string
        const ytContext = youtubeUrls.length > 0
            ? `\n\nThe user has also provided these YouTube video references for visual style: ${youtubeUrls.join(', ')}`
            : '';

        const charContext = charDescriptions.length > 0
            ? `\n\nCharacter descriptions (with reference images attached):\n${charDescriptions.join('\n')}`
            : '';

        const prompt = `You are an expert anime director and visual aesthetician. Analyze the following script, character references, and style reference images to determine the ideal visual style for this animated project.

Consider:
- The historical era, time period, and world the story is set in
- The look and feel of any attached character reference images
- The visual style of any attached style reference images
- The mood, themes, and tone of the script${charContext}${ytContext}

Based on your analysis, infer:

1. **SETTING**: The historical era, geography, architecture, clothing, props, and world-specific details. Be extremely specific.

2. **STYLE GUIDE**: The ideal anime visual style — art style, color palette, lighting, linework, shading technique, mood. Be concrete with descriptors that AI image generators understand.

3. **NEGATIVE PROMPT**: Things to explicitly exclude to avoid inconsistencies.

Respond in this exact JSON format ONLY — no markdown, no explanation:
{
  "setting": "...",
  "guide": "...",
  "negative_prompt": "..."
}

SCRIPT:
${story.substring(0, 8000)}`;

        // Build contents array: text prompt + character images + style ref images
        const contents: Array<{ text: string } | { inlineData: { mimeType: string; data: string } }> = [
            { text: prompt },
            ...charImageParts,
            ...styleImageParts,
        ];

        const { GoogleGenAI } = await import('@google/genai');
        const ai = new GoogleGenAI({ vertexai: true, project: 'gen-lang-client-0655380841', location: 'us-central1' });

        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: contents,
            config: {
                temperature: 0.3,
                responseMimeType: 'application/json',
            },
        });

        const text = response.text?.trim() || '';

        let parsed;
        try {
            parsed = JSON.parse(text);
        } catch {
            const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/) || text.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                parsed = JSON.parse(jsonMatch[1] || jsonMatch[0]);
            } else {
                throw new Error('Could not parse style inference response');
            }
        }

        return NextResponse.json({
            success: true,
            style: {
                setting: parsed.setting || '',
                guide: parsed.guide || '',
                negative_prompt: parsed.negative_prompt || '',
            },
        });
    } catch (error) {
        console.error('Style inference failed:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to analyze script for style.' },
            { status: 500 }
        );
    }
}
