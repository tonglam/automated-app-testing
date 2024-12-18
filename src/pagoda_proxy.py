import json
import os
from pathlib import Path

from mitmproxy import ctx

# Get the project root directory
project_root = Path(__file__).parent.parent
data_dir = project_root / "data"
os.makedirs(data_dir, exist_ok=True)

class RequestCapture:
    def __init__(self):
        self.captured_requests = []

    def request(self, flow):
        if "searchGoods" in flow.request.pretty_url:
            request_data = {
                "url": flow.request.pretty_url,
                "method": flow.request.method,
                "headers": dict(flow.request.headers),
                "params": dict(flow.request.query),
                "body": (
                    flow.request.content.decode("utf-8")
                    if flow.request.content
                    else None
                ),
            }
            self.captured_requests.append(request_data)

            with open(data_dir / "captured_requests.json", "w", encoding="utf-8") as f:
                json.dump(self.captured_requests, f, ensure_ascii=False, indent=2)

    def response(self, flow):
        if "searchGoods" in flow.request.pretty_url and flow.response:
            try:
                response_data = json.loads(flow.response.content)
                if "onSaleList" in str(response_data):
                    with open(data_dir / "search_results.json", "w", encoding="utf-8") as f:
                        json.dump(response_data, f, ensure_ascii=False, indent=2)
                    ctx.log.info("Successfully captured search results")
            except Exception as e:
                ctx.log.error(f"Failed to process response: {str(e)}")


addons = [RequestCapture()]
