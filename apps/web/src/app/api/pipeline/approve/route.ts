import { NextResponse } from 'next/server';
import { existsSync } from 'fs';
import { readFile } from 'fs/promises';
import { exec } from 'child_process';

const PROJECT_ROOT = '/Users/ashwink/Desktop/ZSC-pipeline';
const STATE_FILE = `${PROJECT_ROOT}/output/pipeline_state.json`;

export async function POST() {
    try {
        if (!existsSync(STATE_FILE)) {
            return NextResponse.json(
                { success: false, error: 'No pipeline state found. Run the full pipeline first.' },
                { status: 400 }
            );
        }

        const stateData = JSON.parse(await readFile(STATE_FILE, 'utf-8'));
        const shots = (stateData.scenes || []).flatMap((s: any) => s.shots || []);

        const hasPromptsNoKeyframes = shots.some((s: any) => s.image_prompt && !s.keyframe_path);
        const hasKeyframesNoClips = shots.some((s: any) => s.keyframe_path && !s.clip_path);

        if (hasPromptsNoKeyframes) {
            // Phase 1: Generate all keyframes
            console.log('Generating keyframes for all shots...');
            const cmd = `cd ${PROJECT_ROOT} && set -a && source .env && set +a && export GCP_PROJECT_ID=gen-lang-client-0655380841 && source .venv/bin/activate || true && python -m src.generation.generate_single --config config/default_config.yaml --all > /tmp/pipeline_keyframes.log 2>&1 &`;

            exec(cmd, (error) => {
                if (error) console.error('Keyframe gen exec error:', error);
            });

            return NextResponse.json({
                success: true,
                phase: 'keyframes',
                message: 'Keyframe generation started for all shots!',
            });

        } else if (hasKeyframesNoClips) {
            // Phase 2: Generate videos (existing behavior)
            console.log('Approve & Generate Video: Triggering resume pipeline...');
            const cmd = `cd ${PROJECT_ROOT} && set -a && source .env && set +a && export GCP_PROJECT_ID=gen-lang-client-0655380841 && source .venv/bin/activate || true && python -m src.main resume --config config/default_config.yaml > /tmp/pipeline_resume.log 2>&1 &`;

            exec(cmd, (error) => {
                if (error) console.error('Resume exec error:', error);
            });

            return NextResponse.json({
                success: true,
                phase: 'video',
                message: 'Video generation started for approved keyframes.',
            });

        } else {
            return NextResponse.json({
                success: false,
                error: 'No shots ready for processing. Ensure prompts or keyframes exist.',
            }, { status: 400 });
        }
    } catch (error) {
        console.error('Approve failed:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to start generation' },
            { status: 500 }
        );
    }
}
