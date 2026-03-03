import os
import json
import logging
from typing import Optional
from google.cloud import storage

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages file storage, transparently supporting local files or GCS."""
    def __init__(self, config: dict):
        self.config = config
        self.bucket_name = config.get("pipeline", {}).get("gcs_bucket")
        self.output_dir = config.get("pipeline", {}).get("output_dir", "./output")
        self.is_cloud = bool(self.bucket_name)

        if self.is_cloud:
            try:
                self.client = storage.Client()
                
                try:
                    self.bucket = self.client.get_bucket(self.bucket_name)
                    logger.info(f"Initialized existing Cloud Storage bucket: {self.bucket_name}")
                except Exception:
                    self.bucket = self.client.create_bucket(self.bucket_name, location="us-central1")
                    logger.info(f"Created new Cloud Storage bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}. Falling back to local.")
                self.is_cloud = False

        if not self.is_cloud:
            logger.info(f"Running in local storage mode using {self.output_dir}")
            os.makedirs(self.output_dir, exist_ok=True)

    def write_bytes(self, data: bytes, destination_path: str) -> str:
        """Writes raw bytes to either local or GCS."""
        if self.is_cloud:
            blob_path = destination_path.lstrip("./output/").lstrip("/")
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(data)
            return f"gs://{self.bucket_name}/{blob_path}"
        else:
            local_path = os.path.join(self.output_dir, destination_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            return local_path
            
    def read_bytes(self, source_path: str) -> Optional[bytes]:
        """Reads raw bytes from either local or GCS."""
        if source_path.startswith("gs://"):
            if not self.is_cloud:
                logger.error("Cannot read GCS path without GCS configured")
                return None
            blob_path = source_path.replace(f"gs://{self.bucket_name}/", "")
            blob = self.bucket.blob(blob_path)
            return blob.download_as_bytes()
        else:
            if not os.path.exists(source_path):
                return None
            with open(source_path, "rb") as f:
                return f.read()

    def download_to_local(self, source_path: str, local_destination: str) -> Optional[str]:
        """Downloads a cloud file to a temporary local location (e.g. for ffmpeg processing)."""
        if not source_path.startswith("gs://"):
            return source_path # Already local

        if not self.is_cloud:
            logger.error("GCS not configured, cannot download.")
            return None

        blob_path = source_path.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(blob_path)
        
        os.makedirs(os.path.dirname(local_destination), exist_ok=True)
        blob.download_to_filename(local_destination)
        return local_destination
        
    def upload_from_local(self, local_source: str, destination_path: str) -> str:
        """Uploads a local file to the cloud (e.g. post ffmpeg processing)."""
        if self.is_cloud:
            blob_path = destination_path.lstrip("./output/").lstrip("/")
            blob = self.bucket.blob(blob_path)
            blob.upload_from_filename(local_source)
            return f"gs://{self.bucket_name}/{blob_path}"
        else:
            # If not cloud, we might just copy it or it's already there
            if os.path.abspath(local_source) != os.path.abspath(destination_path):
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                import shutil
                shutil.copy2(local_source, destination_path)
            return destination_path
            
    def write_json(self, data: dict, destination_path: str) -> str:
        """Writes dict data as JSON"""
        json_data = json.dumps(data, indent=2).encode('utf-8')
        return self.write_bytes(json_data, destination_path)
        
    def read_json(self, source_path: str) -> Optional[dict]:
        """Reads JSON data from storage"""
        data_bytes = self.read_bytes(source_path)
        if hasattr(data_bytes, 'decode'):
            return json.loads(data_bytes.decode('utf-8'))
        return None
