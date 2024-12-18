import json
import time
import logging

from request_replayer import RequestReplayer
from search_keywords import SEARCH_KEYWORDS
from mitmproxy import io
from mitmproxy.exceptions import FlowReadException
from mitmproxy.flow import Flow

# Set up logging with debug level for development
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_flow_to_json():
    """Convert mitmproxy flow file to JSON format."""
    captured_requests = []
    
    try:
        logger.info("Opening traffic.flow file...")
        with open('traffic.flow', 'rb') as fp:
            reader = io.FlowReader(fp)
            flow_count = 0
            for flow in reader.stream():
                flow_count += 1
                try:
                    # Log detailed flow information for debugging
                    logger.debug(f"Processing flow #{flow_count}")
                    logger.debug(f"Flow object type: {type(flow)}")
                    logger.debug(f"Flow object attributes: {dir(flow)}")
                    
                    if not isinstance(flow, Flow):
                        logger.warning(f"Flow object is not an instance of mitmproxy.flow.Flow: {type(flow)}")
                        continue

                    # Check if flow has request attribute using getattr
                    request = getattr(flow, 'request', None)
                    if request is None:
                        logger.warning(f"Flow object missing request attribute: {type(flow)}")
                        continue
                    
                    # Check if request has pretty_url
                    pretty_url = getattr(request, 'pretty_url', None)
                    if pretty_url is None:
                        logger.warning("Flow request missing pretty_url attribute")
                        continue
                    
                    # Log all URLs being processed
                    logger.info(f"Processing URL: {pretty_url}")
                    
                    if 'search' in pretty_url.lower():
                        request_data = {
                            'url': pretty_url,
                            'method': getattr(request, 'method', None),
                            'headers': dict(getattr(request, 'headers', {})),
                        }
                        
                        # Handle request body
                        if hasattr(request, 'content') and request.content:
                            try:
                                body = request.content.decode('utf-8', errors='ignore')
                                request_data['body'] = body
                            except Exception as e:
                                logger.error(f"Could not decode request body for {pretty_url}: {str(e)}")
                                continue
                        
                        captured_requests.append(request_data)
                        logger.info(f"Successfully captured request for URL: {pretty_url}")
                except AttributeError as ae:
                    logger.error(f"Attribute error processing flow: {str(ae)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing flow: {str(e)}")
                    continue
                    
        if not captured_requests:
            logger.warning("No search requests found in traffic.flow")
            return False
            
    except FileNotFoundError:
        logger.error("No traffic.flow file found")
        return False
    except FlowReadException as e:
        logger.error(f"Error reading flow file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing flow file: {str(e)}")
        return False
        
    try:
        with open('captured_requests.json', 'w', encoding='utf-8') as f:
            json.dump(captured_requests, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save captured requests: {str(e)}")
        return False

def search_all_keywords():
    """Search for all keywords using the captured API requests."""
    # First convert the flow file to JSON
    if not convert_flow_to_json():
        logger.error("Failed to convert flow file to JSON")
        return
    
    replayer = RequestReplayer()
    captured_requests = []

    try:
        captured = replayer.load_captured_requests()
        if not captured:
            logger.error("No captured requests found")
            return
            
        original_request = captured[0]
        if not original_request.get('body'):
            logger.error("No request body found in captured request")
            return

        # First, save the initial "苹果" search result
        try:
            with open(f"search_results_苹果.json", "w", encoding="utf-8") as f:
                json.dump(original_request, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save initial search result: {str(e)}")
            return

        for keyword in SEARCH_KEYWORDS:
            if keyword == "苹果":
                continue

            logger.info(f"Searching for: {keyword}")

            try:
                # Create a copy of the original request to modify
                current_request = original_request.copy()
                
                # Parse and modify the body
                try:
                    body_dict = json.loads(current_request["body"])
                    body_dict["keywords"] = keyword
                    current_request["body"] = json.dumps(body_dict, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    logger.error(f"Could not parse request body as JSON: {str(e)}")
                    continue

                # Store the modified request
                captured_requests.append(current_request)

                # Replay the request
                result = replayer.replay_request(current_request)
                if result:
                    with open(f"search_results_{keyword}.json", "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                else:
                    logger.error(f"Failed to get results for keyword: {keyword}")

                time.sleep(0.5)  # 500ms delay between API calls

            except Exception as e:
                logger.error(f"Error processing keyword {keyword}: {str(e)}")
                continue

        # Save all captured requests
        try:
            with open("captured_requests.json", "w", encoding="utf-8") as f:
                json.dump(captured_requests, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save captured requests: {str(e)}")

    except Exception as e:
        logger.error(f"Error in search_all_keywords: {str(e)}")


if __name__ == "__main__":
    search_all_keywords()
