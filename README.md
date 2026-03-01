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

## Local Usage
Run the pipeline via the CLI entrypoint:
```bash
python -m src.main run --config config/example_episode.yaml --story story.txt
```

## Cloud Run Deployment (100% Cloud Native)
To deploy the pipeline as a Google Cloud Run Job (which executes in the cloud and saves everything to Google Cloud Storage instead of your local disk):

1. Set `gcs_bucket: "your-bucket-name"` in `config/default_config.yaml`
2. Run the deployment script:
```bash
./scripts/deploy_cloud_run.sh
```
3. To execute the pipeline in the cloud:
```bash
gcloud run jobs execute anime-pipeline-job --region us-central1
```
