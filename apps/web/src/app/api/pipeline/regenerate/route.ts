import { NextResponse } from 'next/server';
import { existsSync } from 'fs';
import { readFile, writeFile } from 'fs/promises';
import { exec } from 'child_process';

const PROJECT_ROOT = '/Users/ashwink/Desktop/ZSC-pipeline';
const STATE_FILE = `${PROJECT_ROOT}/output/pipeline_state.json`;

export async function POST(request: Request) {
    try {
        const { shot_id, image_prompt, image_prompt_end } = await request.json();

        if (!shot_id) {
            return NextResponse.json({ success: false, error: 'shot_id required' }, { status: 400 });
        }

        if (!existsSync(STATE_FILE)) {
            return NextResponse.json({ success: false, error: 'No pipeline state found.' }, { status: 400 });
        }

        // If prompts were edited, update the state file first
        if (image_prompt !== undefined || image_prompt_end !== undefined) {
            const stateData = JSON.parse(await readFile(STATE_FILE, 'utf-8'));
            let found = false;
            for (const scene of stateData.scenes || []) {
                for (const shot of scene.shots || []) {
                    if (shot.id === shot_id) {
                        if (image_prompt !== undefined) shot.image_prompt = image_prompt;
                        if (image_prompt_end !== undefined) shot.image_prompt_end = image_prompt_end;
                        // Clear old keyframes so they get regenerated
                        shot.keyframe_path = null;
                        shot.keyframe_end_path = null;
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            if (!found) {
                return NextResponse.json({ success: false, error: `Shot ${shot_id} not found` }, { status: 404 });
            }
            await writeFile(STATE_FILE, JSON.stringify(stateData, null, 2));
        }

        // Build CLI command for single-shot regeneration
        const promptArg = image_prompt ? `--prompt '${image_prompt.replace(/'/g, "'\\''")}'` : '';
        const promptEndArg = image_prompt_end ? `--prompt-end '${image_prompt_end.replace(/'/g, "'\\''")}'` : '';

        const cmd = `cd ${PROJECT_ROOT} && set -a && source .env && set +a && export GCP_PROJECT_ID=gen-lang-client-0655380841 && source .venv/bin/activate || true && python -m src.generation.generate_single --config config/default_config.yaml --shot-id ${shot_id} ${promptArg} ${promptEndArg} > /tmp/pipeline_regen.log 2>&1 &`;

        console.log(`Regenerating keyframe for ${shot_id}...`);
        exec(cmd, (error) => {
            if (error) console.error('Regen exec error:', error);
        });

        return NextResponse.json({
            success: true,
            message: `Regenerating keyframe for ${shot_id}...`,
        });
    } catch (error) {
        console.error('Regenerate failed:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to regenerate keyframe' },
            { status: 500 }
        );
    }
}
