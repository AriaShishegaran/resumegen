import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class OllamaClient:
    def __init__(self, host="localhost", port=11434):
        self.base_url = f"http://{host}:{port}"
        # Updated model to a more capable one
        self.model = "llama3.2"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt):
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 2048  # Allow for longer responses
                },
                "stream": False
            }
            logging.debug(f"Sending payload to /api/generate: {json.dumps(payload, indent=2)}")
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Increased timeout for longer processing
            )
            response.raise_for_status()
            result = response.json()
            if 'response' in result:
                return result['response'].strip()
            else:
                logging.error(f"Unexpected response format: {result}")
                raise RuntimeError(f"Unexpected response format: {result}")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            raise RuntimeError(f"HTTP error occurred: {http_err} - Response: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception: {e}")
            raise RuntimeError("Failed to communicate with Ollama")
        except Exception as e:
            logging.error(f"Other error occurred: {e}")
            raise RuntimeError("Failed to communicate with Ollama")
