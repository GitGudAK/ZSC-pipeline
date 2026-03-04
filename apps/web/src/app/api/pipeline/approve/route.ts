import { NextResponse } from 'next/server';
import { existsSync } from 'fs';
import { exec } from 'child_process';

const PROJECT_ROOT = '/Users/ashwink/Desktop/ZSC-pipeline';
const STATE_FILE = `${PROJECT_ROOT}/output/pipeline_state.json`;

export async function POST() {
    try {
        // Verify state file exists (which means storyboard has data to approve)
        if (!existsSync(STATE_FILE)) {
            return NextResponse.json(
                { success: false, error: 'No pipeline state found. Run the full pipeline first.' },
                { status: 400 }
            );
        }

        console.log('Approve & Generate Video: Triggering resume pipeline...');

        // Execute the resume CLI command which generates videos for approved keyframes + stitches
        const cmd = `cd ${PROJECT_ROOT} && set -a && source .env && set +a && export GCP_PROJECT_ID=gen-lang-client-0655380841 && source .venv/bin/activate || true && python -m src.main resume --config config/default_config.yaml > /tmp/pipeline_resume.log 2>&1 &`;

        exec(cmd, (error) => {
            if (error) console.error('Resume exec error:', error);
        });

        return NextResponse.json({
            success: true,
            message: 'Video generation started for approved keyframes.'
        });
    } catch (error) {
        console.error('Approve & Generate failed:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to start video generation' },
            { status: 500 }
        );
    }
}
