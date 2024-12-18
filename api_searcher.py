import json
import time

from request_replayer import RequestReplayer
from search_keywords import SEARCH_KEYWORDS


def search_all_keywords():
    replayer = RequestReplayer()

    try:
        captured = replayer.load_captured_requests()
        original_request = captured[0]

        # First, save the initial "苹果" search result
        with open(f"search_results_苹果.json", "w", encoding="utf-8") as f:
            json.dump(original_request, f, ensure_ascii=False, indent=2)

        # Load existing captured requests if file exists
        try:
            with open("captured_requests.json", "r", encoding="utf-8") as f:
                captured_requests = json.load(f)
        except FileNotFoundError:
            captured_requests = []

        for keyword in SEARCH_KEYWORDS:
            if keyword == "苹果":
                continue

            print(f"\nSearching for: {keyword}")

            body_dict = json.loads(original_request["body"])
            body_dict["keywords"] = keyword
            original_request["body"] = json.dumps(body_dict, ensure_ascii=False)

            # Store and save the request immediately
            current_request = original_request.copy()
            captured_requests.append(current_request)
            with open("captured_requests.json", "w", encoding="utf-8") as f:
                json.dump(captured_requests, f, ensure_ascii=False, indent=2)

            result = replayer.replay_request(original_request)
            if result:
                with open(f"search_results_{keyword}.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

            time.sleep(0.5)  # 500ms delay between API calls

    except Exception as e:
        print(f"Error in search_all_keywords: {str(e)}")


if __name__ == "__main__":
    search_all_keywords()
