# llm_client.py

import requests
import json
import logging
import time
import subprocess
from tenacity import retry, stop_after_attempt, wait_exponential
from abc import ABC, abstractmethod
from user_interface import UserInterface

class BaseModelClient(ABC):
    @abstractmethod
    def generate(self, prompt, system_message=None, max_tokens=None):
        pass

class OllamaClient(BaseModelClient):
    def __init__(self, host="localhost", port=11434, model="llama3.2"):
        self.base_url = f"http://{host}:{port}"
        self.model = model
        self.endpoint = "/api/generate"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt, system_message=None, max_tokens=None):
        # Existing implementation remains unchanged
        pass

class LMStudioClient(BaseModelClient):
    def __init__(self, host="localhost", port=1234, model="Llama-3.2-3B-Instruct-4bit", model_path=None):
        self.base_url = f"http://{host}:{port}"
        self.model = model
        self.model_path = model_path
        self.endpoint = "/v1/completions"  # Use /v1/completions for non-chat models

        # Ensure the model is loaded
        self.ensure_model_loaded()

    def ensure_model_loaded(self):
        try:
            # Check if the model is already loaded
            response = requests.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            model_ids = [model['id'] for model in data.get('data', [])]
            if self.model in model_ids:
                UserInterface.info(f"Model '{self.model}' is already loaded.")
                return
            else:
                if not self.model_path:
                    raise RuntimeError("Model is not loaded and no model path provided to load it.")
                UserInterface.info(f"Model '{self.model}' is not loaded. Loading model '{self.model_path}' with identifier '{self.model}'...")
                # Run the command to load the model
                command = ['lms', 'load', self.model_path, '--identifier', self.model]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Wait for the model to be loaded
                while True:
                    # Check if the process has terminated
                    retcode = process.poll()
                    if retcode is not None:
                        # Process has terminated
                        stdout, stderr = process.communicate()
                        if retcode != 0:
                            # Command failed
                            UserInterface.error(f"Failed to load model '{self.model}'.")
                            logging.error(f"lms load command failed with exit code {retcode}")
                            logging.error(f"stdout: {stdout.decode()}")
                            logging.error(f"stderr: {stderr.decode()}")
                            raise RuntimeError(f"Failed to load model '{self.model}' in LMStudio.")
                        else:
                            # Command succeeded
                            UserInterface.success(f"Model '{self.model}' loaded successfully.")
                            break
                    else:
                        # Process still running
                        time.sleep(5)
                        # Check if the model is now loaded
                        response = requests.get(f"{self.base_url}/v1/models")
                        response.raise_for_status()
                        data = response.json()
                        model_ids = [model['id'] for model in data.get('data', [])]
                        if self.model in model_ids:
                            UserInterface.success(f"Model '{self.model}' loaded successfully.")
                            break
                        else:
                            UserInterface.info("Waiting for the model to load...")
        except Exception as e:
            logging.error(f"Error ensuring model is loaded: {str(e)}")
            raise RuntimeError(f"Failed to load model '{self.model}' in LMStudio: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt, system_message=None, max_tokens=None):
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer lm-studio'
            }

            # LMStudio's /v1/completions endpoint does not use messages
            if system_message:
                prompt = f"{system_message}\n\n{prompt}"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.0,
                "max_tokens": max_tokens if max_tokens is not None else 512,
                "top_p": 0.1,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.5,
                "stop": None,
                "stream": False,
                "logit_bias": {},
                "seed": 42
            }

            logging.debug(f"Sending payload to {self.endpoint}: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            response = requests.post(
                f"{self.base_url}{self.endpoint}",
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['text'].strip()
            else:
                logging.error(f"Unexpected response format: {result}")
                raise RuntimeError(f"Unexpected response format: {result}")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            raise RuntimeError(f"HTTP error occurred: {http_err} - Response: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception: {e}")
            raise RuntimeError("Failed to communicate with the LMStudio server.")
        except Exception as e:
            logging.error(f"Other error occurred: {e}")
            raise RuntimeError(f"Failed to communicate with the LMStudio server: {str(e)}")

class ModelClientFactory:
    @staticmethod
    def create_client(client_type="ollama", **kwargs):
        if client_type.lower() == "ollama":
            return OllamaClient(**kwargs)
        elif client_type.lower() == "lmstudio":
            return LMStudioClient(**kwargs)
        raise ValueError(f"Unsupported client type: {client_type}")