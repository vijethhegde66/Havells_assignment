"""API client for communicating with the backend."""
import requests
from typing import Optional, Dict, Any

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/session/create",
            params={"session_id": session_id} if session_id else {}
        )
        response.raise_for_status()
        return response.json()
    
    def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/chat",
            json={"session_id": session_id, "message": message}
        )
        response.raise_for_status()
        return response.json()
    
    def get_stats(self, session_id: str) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/session/{session_id}/stats"
        )
        response.raise_for_status()
        return response.json()
    
    def get_history(self, session_id: str) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/session/{session_id}/history"
        )
        response.raise_for_status()
        return response.json()
    
    def reset_session(self, session_id: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/session/{session_id}/reset"
        )
        response.raise_for_status()
        return response.json()
    
    def inject_failure(self, session_id: str, failure_type: str, duration: int) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/session/{session_id}/device/inject-failure",
            json={"failure_type": failure_type, "duration": duration}
        )
        response.raise_for_status()
        return response.json()
    
    def clear_failure(self, session_id: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/session/{session_id}/device/clear-failure"
        )
        response.raise_for_status()
        return response.json()
    
    def get_device_status(self, session_id: str) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/session/{session_id}/device/status"
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/")
            return response.status_code == 200
        except:
            return False
