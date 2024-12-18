import json
import logging

import requests

logger = logging.getLogger(__name__)


class RequestReplayer:
    def __init__(self, capture_file="captured_requests.json"):
        self.capture_file = capture_file

    def load_captured_requests(self):
        try:
            with open(self.capture_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Capture file {self.capture_file} not found")
            return []
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in capture file {self.capture_file}")
            return []

    def replay_request(self, request_data, modified_params=None):
        """Replay a captured request with optional parameter modifications"""
        try:
            # Validate required fields
            required_fields = ["method", "url", "headers"]
            for field in required_fields:
                if field not in request_data:
                    logger.error(f"Missing required field: {field}")
                    return None

            # Build request kwargs
            kwargs = {
                "method": request_data["method"],
                "url": request_data["url"],
                "headers": request_data["headers"],
            }

            # Add optional fields if they exist
            if "params" in request_data:
                params = request_data["params"].copy() if request_data["params"] else {}
                if modified_params:
                    params.update(modified_params)
                kwargs["params"] = params

            if "body" in request_data and request_data["body"]:
                kwargs["data"] = request_data["body"]

            # Make the request
            response = requests.request(**kwargs)
            
            # Validate response
            if response.status_code != 200:
                logger.error(f"Request failed with status code: {response.status_code}")
                return None

            try:
                return response.json()
            except json.JSONDecodeError:
                logger.error("Failed to parse response as JSON")
                return None

        except Exception as e:
            logger.error(f"Failed to replay request: {str(e)}")
            return None

    def replay_with_modifications(self, param_variations):
        """Replay requests with different parameter variations"""
        results = []
        try:
            captured = self.load_captured_requests()
            if not captured:
                logger.error("No captured requests found")
                return []

            for request in captured:
                for params in param_variations:
                    result = self.replay_request(request, params)
                    if result:
                        results.append(result)

            return results
        except Exception as e:
            logger.error(f"Failed to replay modifications: {str(e)}")
            return []
