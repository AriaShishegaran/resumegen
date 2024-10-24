import json
import logging
import docx
from docx.shared import Pt
from json_repair import repair_json
from datetime import datetime
from user_interface import UserInterface
from docx.oxml import OxmlElement

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
        UserInterface.progress("Sending resume to LLM for parsing...")
        prompt = (
            f"Parse the following resume text into sections.\n\n"
            f"Resume Text:\n{content}\n\n"
            "Instructions:\n"
            "1. Extract the resume into sections such as 'Contact Information', 'Summary', 'Work Experience', 'Education', etc.\n"
            "2. Ensure each section is correctly labeled and contains all the relevant information from the resume.\n"
            "3. Do not summarize or omit any details; preserve all original content exactly as it is.\n"
            "4. Ensure the 'Summary' section is a string, not an object.\n"
            "5. Return the result strictly as valid JSON.\n"
            "Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume parsing:\n{response}")

        response = self._clean_json_response(response)

        try:
            resume_dict = json.loads(response)
            return resume_dict
        except json.JSONDecodeError:
            # Use json_repair to fix the JSON
            UserInterface.info("Attempting to repair JSON for resume parsing...")
            repaired_response = repair_json(response)
            try:
                resume_dict = json.loads(repaired_response)
                UserInterface.success("JSON repair successful for resume parsing")
                return resume_dict
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse repaired JSON: {e}")
                UserInterface.error("Failed to repair JSON for resume parsing")
                raise RuntimeError("Failed to parse JSON response from LLM for resume parsing")

    def optimize_resume(self, resume_dict, requirements):
        UserInterface.progress("Optimizing resume sections...")
        prompt = (
            f"Optimize the following resume to highlight the key requirements for a job application.\n\n"
            f"Resume:\n{json.dumps(resume_dict, indent=2)}\n\n"
            f"Key Requirements:\n- " + '\n- '.join(requirements) + "\n\n"
            "Instructions:\n"
            "1. Review each section of the resume and enhance it by incorporating relevant keywords and phrases from the key requirements.\n"
            "2. Do not remove any existing content; only add or modify to better match the job requirements.\n"
            "3. Ensure that all original details are preserved.\n"
            "4. Ensure the 'Summary' section is a string, not an object.\n"
            "5. Return the optimized resume strictly as valid JSON.\n"
            "Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume optimization:\n{response}")

        response = self._clean_json_response(response)

        try:
            optimized_resume = json.loads(response)
            # Update the resume_dict with optimized content
            resume_dict.update(optimized_resume)
        except json.JSONDecodeError:
            # Use json_repair to fix the JSON
            UserInterface.info("Attempting to repair JSON for resume optimization...")
            repaired_response = repair_json(response)
            try:
                optimized_resume = json.loads(repaired_response)
                UserInterface.success("JSON repair successful for resume optimization")
                resume_dict.update(optimized_resume)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse repaired JSON: {e}")
                UserInterface.error("Failed to repair JSON for resume optimization")
                raise RuntimeError("Failed to parse JSON response from LLM for resume optimization")

    def create_document(self, resume_data, output_path):
        doc = docx.Document()
        # Fix compatibility mode issues
        if not doc.core_properties.created:
            doc.core_properties.created = datetime.now()
        if not doc.core_properties.last_modified_by:
            doc.core_properties.last_modified_by = 'ATS Resume Generator'

        self._remove_compatibility_mode(doc)

        for section, content in resume_data.items():
            doc.add_heading(section, level=1)
            self._add_content(doc, content)
        doc.save(output_path)

    def _remove_compatibility_mode(self, doc):
        """
        Removes the compatibility mode settings from the document to prevent it from opening in compatibility mode.
        """
        settings = doc.settings.element
        compat = settings.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}compat')
        if compat is not None:
            settings.remove(compat)
            UserInterface.info("Removed compatibility mode from the document settings.")

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
