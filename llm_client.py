import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class OllamaClient:
    def __init__(self, host="localhost", port=11434):
        self.base_url = f"http://{host}:{port}"
        self.model = "llama3.2"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt, system_message=None):
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": 0.0,         # Set temperature to 0 for deterministic output
                    "max_tokens": 4096,
                    "top_p": 0.1,               # Lowered top_p to reduce sampling randomness
                    "top_k": 20,                # Lowered top_k to limit to most probable tokens
                    "repeat_penalty": 1.2,      # Increased to discourage repetition
                    "frequency_penalty": 0.5,   # Penalize frequent tokens
                    "presence_penalty": 0.5,    # Penalize tokens that have already appeared
                    "mirostat": 2,              # Enable Mirostat 2.0 for controlling perplexity
                    "mirostat_tau": 5.0,        # Default value for Mirostat tau
                    "mirostat_eta": 0.1,        # Default value for Mirostat eta
                    "seed": 42
                },
                "stream": False
            }
            if system_message:
                payload["system"] = system_message

            logging.debug(f"Sending payload to /api/generate: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300  # Increased timeout for longer processing
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
            raise RuntimeError("Failed to communicate with the LLM server.")
        except Exception as e:
            logging.error(f"Other error occurred: {e}")
            raise RuntimeError(f"Failed to communicate with the LLM server: {str(e)}")
