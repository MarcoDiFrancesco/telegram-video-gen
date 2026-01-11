"""Veo API wrapper."""
import time
import base64
from typing import Dict
import requests
from google.auth import default
from google.auth.transport.requests import Request

from config.settings import GOOGLE_CLOUD_PROJECT_ID, GOOGLE_CLOUD_LOCATION


class VeoClient:
    """Client for interacting with Google Veo API."""
    
    def __init__(self):
        """Initialize Veo client."""
        self.project_id = GOOGLE_CLOUD_PROJECT_ID
        self.location = GOOGLE_CLOUD_LOCATION
        self.credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1"
    
    def _request(self, endpoint: str, body: Dict) -> Dict:
        """Make authenticated API request."""
        self.credentials.refresh(Request())
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, json=body, headers={"Authorization": f"Bearer {self.credentials.token}"})
        response.raise_for_status()
        return response.json()
    
    def generate_video(
        self,
        prompt: str,
        model: str,
        duration_seconds: int = 8,
        resolution: str = "720p",
        generate_audio: bool = True,
        sample_count: int = 1
    ) -> Dict:
        """Generate video using Veo API."""
        endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{model}:predictLongRunning"
        body = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "durationSeconds": duration_seconds,
                "resolution": resolution,
                "generateAudio": generate_audio,
                "sampleCount": sample_count
            }
        }
        result = self._request(endpoint, body)
        if not (operation_name := result.get("name")):
            raise ValueError(f"Failed to get operation name: {result}")
        return {"operation_name": operation_name, "model": model}
    
    def poll_operation(self, operation_name: str, model: str, max_wait_time: int = 600) -> Dict:
        """Poll for operation completion."""
        endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{model}:fetchPredictOperation"
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                result = self._request(endpoint, {"operationName": operation_name})
                if result.get("done", False):
                    if "error" in result:
                        return {"done": True, "error": str(result["error"]), "videos": []}
                    response_data = result.get("response", {})
                    return {
                        "done": True,
                        "videos": response_data.get("videos", []),
                        "raiMediaFilteredCount": response_data.get("raiMediaFilteredCount", 0),
                        "error": None
                    }
                time.sleep(5)
            except Exception as e:
                return {"done": True, "error": f"API request failed: {str(e)}", "videos": []}
        return {"done": False, "error": "Operation timed out", "videos": []}
    
    def download_video(self, video_data: Dict) -> bytes:
        """Download video from GCS URI or decode from base64."""
        if "gcsUri" in video_data:
            from google.cloud import storage
            bucket_name, blob_path = video_data["gcsUri"].replace("gs://", "").split("/", 1)
            return storage.Client().bucket(bucket_name).blob(blob_path).download_as_bytes()
        elif "bytesBase64Encoded" in video_data:
            return base64.b64decode(video_data["bytesBase64Encoded"])
        raise ValueError("Video data must contain either 'gcsUri' or 'bytesBase64Encoded'")

