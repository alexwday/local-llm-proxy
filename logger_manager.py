"""Logging manager for API calls and server events."""

import time
from collections import deque
from typing import Dict, List, Any


class LoggerManager:
    """Manages in-memory logs for API calls and server events."""

    def __init__(self, max_logs: int = 100):
        self.max_logs = max_logs
        self.api_calls = deque(maxlen=max_logs)
        self.server_events = deque(maxlen=max_logs)

    def log_api_call(self, method: str, path: str, status: int, duration_ms: int, request_data: Any = None, response_data: Any = None):
        """Log an API call."""
        self.api_calls.append({
            'timestamp': time.time(),
            'method': method,
            'path': path,
            'status': status,
            'duration_ms': duration_ms,
            'request': request_data,
            'response': response_data,
        })

    def log_server_event(self, level: str, message: str, data: Any = None):
        """Log a server event."""
        self.server_events.append({
            'timestamp': time.time(),
            'level': level,
            'message': message,
            'data': data,
        })

    def get_api_calls(self) -> List[Dict]:
        """Get all API call logs."""
        return list(self.api_calls)

    def get_server_events(self) -> List[Dict]:
        """Get all server event logs."""
        return list(self.server_events)

    def get_logs(self) -> Dict[str, List]:
        """Get all logs."""
        return {
            'apiCalls': self.get_api_calls(),
            'serverEvents': self.get_server_events(),
        }

    def clear_logs(self):
        """Clear all logs."""
        self.api_calls.clear()
        self.server_events.clear()
