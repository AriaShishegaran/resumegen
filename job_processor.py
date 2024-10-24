import requests
import json
import logging
from bs4 import BeautifulSoup
from json_repair import repair_json
from user_interface import UserInterface

class JobProcessor:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.headers = {
            'User-Agent': 'Mozilla/5.0'
        }

    def fetch_and_parse(self, url):
        try:
            if 'greenhouse.io' in url:
                parts = url.rstrip('/').split('/')
                job_id = parts[-1].split('#')[0]
                company = parts[-3]
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
                response = requests.get(api_url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get('title', ''), data.get('content', '')
            else:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._parse_html_content(soup)
        except Exception as e:
            logging.error(f"Error processing job posting: {str(e)}")
            raise RuntimeError("Failed to process job posting")

    def _parse_html_content(self, soup):
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ''
        description = soup.get_text(separator=' ', strip=True)

        prompt = (
            f"Extract the job title and description from this text:\n\n"
            f"{description}\n\n"
            'Format as JSON: {"job_title": "title", "job_description": "description"}\n'
            "Return the result strictly as valid JSON. Do not include any additional text, explanations, or code block markers."
        )

        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for job parsing:\n{response}")

        response = self._clean_json_response(response)

        attempts = 0
        while True:
            try:
                data = json.loads(response)
                if attempts > 0:
                    UserInterface.success(f"JSON repair successful after {attempts} attempt(s) for job parsing.")
                return data.get("job_title", ""), data.get("job_description", "")
            except json.JSONDecodeError as e:
                if attempts == 0:
                    UserInterface.info("Attempting to repair JSON for job parsing...")
                attempts += 1
                if attempts > 3:
                    logging.error(f"Failed to parse repaired JSON after {attempts} attempts: {e}")
                    UserInterface.error("Failed to repair JSON for job parsing")
                    raise RuntimeError("Failed to parse JSON response from LLM for job parsing")
                response = repair_json(response)
                UserInterface.info(f"JSON repair attempt {attempts} for job parsing.")

    def extract_requirements(self, description):
        prompt = (
            f"Extract the key requirements from this job description:\n\n"
            f"{description}\n\n"
            "Return as a numbered list.\n"
            "Do not include any additional text or explanations."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for requirements extraction:\n{response}")

        response = self._clean_json_response(response)

        requirements = self._parse_requirements(response)
        if not requirements:
            raise RuntimeError("Failed to extract requirements from LLM response")
        return requirements

    def _parse_requirements(self, text):
        lines = text.strip().split('\n')
        requirements = []
        for line in lines:
            line = line.strip()
            if line:
                requirement = line.lstrip('0123456789.- ').strip()
                requirements.append(requirement)
        return requirements

    def _clean_json_response(self, response):
        response = response.strip()
        if response.startswith('```') and response.endswith('```'):
            response = response[3:-3].strip()
        if response.startswith('json'):
            response = response[4:].strip()
        return response
