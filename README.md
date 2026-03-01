# AI Anime Production Pipeline

This is an AI-powered anime production pipeline, powered natively by Google Cloud and Gemini API.

It takes a written story and converts it into a 20-minute anime episode through an automated pipeline:
1. Story Decomposition (Gemini 3.1 Pro)
2. Shot Planning & Prompt Writing
3. Keyframe Generation (Nano Banana Pro / Imagen 4)
4. Video Generation (Veo 3.1)
5. Video Assembly with FFmpeg

## Setup
1. Define GCP_PROJECT_ID in `.env`
2. Run `scripts/setup_gcp.sh` to enable required services
3. Set your elevenlabs and other extra API keys
4. Make sure you have python 3.11+ and install the requirements via `pip install -e .`

## Usage
Run the pipeline via the CLI entrypoint:
```bash
python -m src.main run --config config/example_episode.yaml --story story.txt
```
