import json
import logging
import docx
from docx.shared import Pt
from json_repair import repair_json
from llm_client import OllamaClient
from datetime import datetime

class ResumeProcessor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def load_template(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to load resume template: {str(e)}")

    def parse_resume(self, content):
        prompt = (
            f"Parse the following resume text into sections.\n\n"
            f"Resume Text:\n{content}\n\n"
            "Instructions:\n"
            "1. Extract the resume into sections such as 'Contact Information', 'Summary', 'Work Experience', 'Education', etc.\n"
            "2. Ensure each section is correctly labeled and contains the relevant information.\n"
            "3. Format the 'Summary' section as a string, not as an object.\n"
            "4. Return the result strictly as valid JSON.\n"
            "5. Do not summarize or omit any details; preserve all original content.\n"
            "Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume parsing:\n{response}")
        print(f"LLM Response for resume parsing:\n{response}")

        response = self._clean_json_response(response)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Use json_repair to fix the JSON
            logging.info("Attempting to repair JSON for resume parsing")
            repaired_response = repair_json(response)
            try:
                return json.loads(repaired_response)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse repaired JSON: {e}")
                raise RuntimeError("Failed to parse JSON response from LLM for resume parsing")

    def optimize_resume(self, resume_dict, requirements):
        prompt = (
            f"Optimize the following resume to highlight the key requirements for a job application.\n\n"
            f"Resume:\n{json.dumps(resume_dict, indent=2)}\n\n"
            f"Key Requirements:\n- " + '\n- '.join(requirements) + "\n\n"
            "Instructions:\n"
            "1. Adjust the resume content to emphasize relevant skills and experiences related to the key requirements.\n"
            "2. Add any missing details from your background that align with the requirements.\n"
            "3. Ensure the 'Summary' section is a string, not an object.\n"
            "4. Return the optimized resume strictly as valid JSON.\n"
            "5. Do not remove any existing content unless it's irrelevant; focus on enhancing and adding relevant details.\n"
            "6. Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume optimization:\n{response}")
        print(f"LLM Response for resume optimization:\n{response}")

        response = self._clean_json_response(response)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Use json_repair to fix the JSON
            logging.info("Attempting to repair JSON for resume optimization")
            repaired_response = repair_json(response)
            try:
                return json.loads(repaired_response)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse repaired JSON: {e}")
                raise RuntimeError("Failed to parse JSON response from LLM for resume optimization")

    def create_document(self, resume_data, output_path):
        doc = docx.Document()
        # Fix compatibility mode issues
        if not doc.core_properties.created:
            doc.core_properties.created = datetime.now()
        if not doc.core_properties.last_modified_by:
            doc.core_properties.last_modified_by = 'ATS Resume Generator'

        for section, content in resume_data.items():
            doc.add_heading(section, level=1)
            self._add_content(doc, content)
        doc.save(output_path)

    def _add_content(self, doc, content, level=1):
        if isinstance(content, str):
            paragraphs = content.strip().split('\n')
            for para in paragraphs:
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.style.font.size = Pt(12)
        elif isinstance(content, list):
            for item in content:
                self._add_content(doc, item, level=level)
        elif isinstance(content, dict):
            for key, value in content.items():
                doc.add_heading(key, level=level+1)
                self._add_content(doc, value, level=level+1)
        else:
            logging.warning(f"Unknown content type: {type(content)}")

    def _clean_json_response(self, response):
        response = response.strip()
        if response.startswith('```') and response.endswith('```'):
            response = response[3:-3].strip()
        if response.startswith('json'):
            response = response[4:].strip()
        return response
