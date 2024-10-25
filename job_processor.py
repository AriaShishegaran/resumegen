import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
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
                job_title, job_description = self._fetch_greenhouse_job(url)
            else:
                job_title, job_description = self._fetch_generic_job(url)
            return job_title, job_description
        except Exception as e:
            logging.error(f"Error processing job posting: {str(e)}")
            raise RuntimeError("Failed to process job posting")

    def _fetch_greenhouse_job(self, url):
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        # Find 'jobs' in path_parts
        if 'jobs' in path_parts:
            jobs_index = path_parts.index('jobs')
            try:
                job_id = path_parts[jobs_index + 1].split('#')[0]
                company = path_parts[jobs_index - 1]
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
                response = requests.get(api_url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                job_title = data.get('title', '')
                job_description = data.get('content', '')
                if not job_title or not job_description:
                    raise RuntimeError("Job title or description not found in Greenhouse API response.")
                return job_title, job_description
            except IndexError:
                raise RuntimeError("Invalid Greenhouse URL format.")
        else:
            raise RuntimeError("Invalid Greenhouse URL: 'jobs' not found in path.")

    def _fetch_generic_job(self, url):
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Attempt to find the job title
        job_title = soup.find('h1')
        if not job_title:
            job_title = soup.find('h2')
        if not job_title:
            raise RuntimeError("Job title not found on the page.")
        job_title_text = job_title.get_text(strip=True)
        # Attempt to find the job description
        description_divs = soup.find_all('div', class_=['description', 'job-description', 'content', 'section'])
        job_description_text = ''
        if description_divs:
            for div in description_divs:
                job_description_text += div.get_text(separator='\n', strip=True) + '\n'
        else:
            # Fallback to the main content
            job_description_text = soup.get_text(separator='\n', strip=True)
        if not job_description_text:
            raise RuntimeError("Job description not found on the page.")
        return job_title_text, job_description_text.strip()

    def extract_requirements(self, job_description):
        prompt = (
            f"Job Description:\n{job_description}\n\n"
            "Instructions:\n"
            "1. Extract the key requirements and qualifications from the job description.\n"
            "2. Return them as a numbered list.\n"
            "3. Do not include any additional text or commentary.\n"
            "Do not include any additional text, explanations, or code block markers."
        )

        try:
            response = self.llm.generate(prompt)
            logging.debug(f"LLM Response for requirements extraction:\n{response}")

            requirements = self._parse_requirements(response)
            if not requirements:
                raise RuntimeError("Failed to extract requirements from LLM response")
            return requirements
        except Exception as e:
            logging.error(f"Exception in extract_requirements: {str(e)}")
            raise RuntimeError(f"Failed to extract requirements: {str(e)}")

    def _parse_requirements(self, text):
        lines = text.strip().split('\n')
        requirements = []
        for line in lines:
            line = line.strip()
            if line:
                requirement = line.lstrip('0123456789.- ').strip()
                requirements.append(requirement)
        return requirements
