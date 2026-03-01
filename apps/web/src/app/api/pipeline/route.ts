import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const { story, styleGuide } = await request.json();

        // In a real implementation, this would:
        // 1. Write the story and style to GCS
        // 2. Trigger the Cloud Run Job via Google Cloud SDK
        // 3. Return the generated Job ID for tracking

        // For this UI scaffolding phase, we mock the successful trigger

        console.log("Mock triggering Cloud Run job for story:", story.substring(0, 50) + "...");

        return NextResponse.json({
            success: true,
            jobId: `run_${Math.random().toString(36).substring(7)}`,
            message: "Pipeline triggered successfully"
        });

    } catch (error) {
        console.error("Pipeline trigger failed:", error);
        return NextResponse.json(
            { success: false, error: "Failed to trigger pipeline" },
            { status: 500 }
        );
    }
}

export async function GET() {
    // In a real implementation, this polls the pipeline_state.json from GCS
    // and checks the status of the Cloud Run Jobs

    return NextResponse.json({
        status: "healthy",
        message: "Pipeline API is running"
    });
}
