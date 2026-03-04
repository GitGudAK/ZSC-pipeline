import { NextResponse } from 'next/server';
import { writeFile, mkdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { unlinkSync } from 'fs';

const PROJECT_ROOT = '/Users/ashwink/Desktop/ZSC-pipeline';
const CHARS_DIR = join(PROJECT_ROOT, 'output', 'characters');
const MANIFEST_PATH = join(CHARS_DIR, 'manifest.json');

interface CharacterEntry {
    name: string;
    description: string;
    imagePath: string;
    fileName: string;
}

async function readManifest(): Promise<CharacterEntry[]> {
    if (!existsSync(MANIFEST_PATH)) return [];
    try {
        const data = await readFile(MANIFEST_PATH, 'utf-8');
        return JSON.parse(data);
    } catch { return []; }
}

async function writeManifest(chars: CharacterEntry[]) {
    await mkdir(CHARS_DIR, { recursive: true });
    await writeFile(MANIFEST_PATH, JSON.stringify(chars, null, 2));
}

// GET — list all characters
export async function GET() {
    const characters = await readManifest();
    return NextResponse.json({ characters });
}

// POST — upload a new character (multipart: image + name + description)
export async function POST(request: Request) {
    try {
        const formData = await request.formData();
        const name = formData.get('name') as string;
        const description = formData.get('description') as string;
        const image = formData.get('image') as File;

        if (!name || !image) {
            return NextResponse.json({ error: 'Name and image are required' }, { status: 400 });
        }

        await mkdir(CHARS_DIR, { recursive: true });

        // Save image
        const safeName = name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
        const ext = image.name.split('.').pop() || 'jpg';
        const fileName = `${safeName}_${Date.now()}.${ext}`;
        const imagePath = join(CHARS_DIR, fileName);

        const bytes = await image.arrayBuffer();
        await writeFile(imagePath, Buffer.from(bytes));

        // Update manifest
        const characters = await readManifest();

        // Remove existing character with same name (overwrite)
        const filtered = characters.filter(c => c.name.toLowerCase() !== name.toLowerCase());

        const entry: CharacterEntry = {
            name,
            description: description || '',
            imagePath: `./output/characters/${fileName}`,
            fileName,
        };

        filtered.push(entry);
        await writeManifest(filtered);

        console.log(`Saved character: ${name} → ${imagePath}`);

        return NextResponse.json({ success: true, character: entry });
    } catch (error) {
        console.error('Character upload failed:', error);
        return NextResponse.json({ error: 'Failed to upload character' }, { status: 500 });
    }
}

// DELETE — remove a character by name
export async function DELETE(request: Request) {
    try {
        const { name } = await request.json();
        const characters = await readManifest();
        const char = characters.find(c => c.name.toLowerCase() === name.toLowerCase());

        if (char) {
            // Delete the image file
            const absPath = join(PROJECT_ROOT, char.imagePath);
            if (existsSync(absPath)) {
                unlinkSync(absPath);
            }
        }

        const filtered = characters.filter(c => c.name.toLowerCase() !== name.toLowerCase());
        await writeManifest(filtered);

        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Character delete failed:', error);
        return NextResponse.json({ error: 'Failed to delete character' }, { status: 500 });
    }
}
