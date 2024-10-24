import json
import logging
import docx
from docx.shared import Pt
from json_repair import repair_json
from datetime import datetime
from user_interface import UserInterface

class ResumeProcessor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def load_template(self, file_path):
        try:
            document = docx.Document(file_path)
            # Extract the document structure
            doc_structure = self.extract_docx_structure(document)
            return document, doc_structure
        except Exception as e:
            raise RuntimeError(f"Failed to load resume template: {str(e)}")

    def extract_docx_structure(self, document):
        """
        Extract the structure and content of the DOCX document.
        """
        doc_structure = {
            "sections": [],
            "paragraphs": [],
            "tables": [],
        }

        # Extract sections
        for section in document.sections:
            sec_details = {
                "orientation": "Landscape" if section.orientation == 1 else "Portrait",
                "page_height": section.page_height,
                "page_width": section.page_width,
                "header_distance": section.header_distance,
                "footer_distance": section.footer_distance,
            }
            doc_structure["sections"].append(sec_details)

        # Extract paragraphs
        for paragraph in document.paragraphs:
            para_details = {
                "text": paragraph.text,
                "style": paragraph.style.name,
                "font": self._get_font_details(paragraph.runs),
                "element": paragraph,
            }
            doc_structure["paragraphs"].append(para_details)

        # Extract tables
        for table in document.tables:
            table_data = self._extract_table_data(table)
            doc_structure["tables"].append(table_data)

        return doc_structure

    def _get_font_details(self, runs):
        if runs:
            run = runs[0]
            return {
                "name": run.font.name,
                "size": run.font.size.pt if run.font.size else None,
                "bold": run.bold,
                "italic": run.italic,
                "underline": run.underline,
            }
        return {}

    def _extract_table_data(self, table):
        table_data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                cell_paragraphs = []
                for paragraph in cell.paragraphs:
                    para_details = {
                        "text": paragraph.text,
                        "style": paragraph.style.name,
                        "font": self._get_font_details(paragraph.runs),
                        "element": paragraph,
                    }
                    cell_paragraphs.append(para_details)
                cell_tables = []
                for nested_table in cell.tables:
                    cell_tables.append(self._extract_table_data(nested_table))
                row_data.append({
                    "paragraphs": cell_paragraphs,
                    "tables": cell_tables,
                    "element": cell,
                })
            table_data.append(row_data)
        return {
            "table": table,
            "data": table_data,
        }

    def parse_resume(self, doc_structure):
        UserInterface.progress("Sending resume to LLM for parsing...")
        UserInterface.info("Parsing resume sections...")

        # Prepare text content for LLM
        resume_text = self._prepare_resume_text(doc_structure)

        prompt = (
            f"Parse the following resume text into sections.\n\n"
            f"Resume Text:\n{resume_text}\n\n"
            "Instructions:\n"
            "1. Extract the resume into sections such as 'Contact Information', 'Summary', 'Work Experience', 'Education', etc.\n"
            "2. Ensure each section is correctly labeled and contains all the relevant information from the resume.\n"
            "3. Do not summarize, paraphrase, or omit any details; preserve all original content exactly as it is.\n"
            "4. Ensure all content is in text format; avoid including boolean values.\n"
            "5. Ensure the 'Summary' section is a string, not an object.\n"
            "6. Return the result strictly as valid JSON.\n"
            "7. Preserve special characters and emojis in the text.\n"
            "Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume parsing:\n{response}")

        response = self._clean_json_response(response)

        attempts = 0
        while True:
            try:
                resume_dict = json.loads(response)
                if attempts > 0:
                    UserInterface.success(f"JSON repair successful after {attempts} attempt(s) for resume parsing.")
                return resume_dict
            except json.JSONDecodeError as e:
                if attempts == 0:
                    UserInterface.info("Attempting to repair JSON for resume parsing...")
                attempts += 1
                if attempts > 3:
                    logging.error(f"Failed to parse repaired JSON after {attempts} attempts: {e}")
                    UserInterface.error("Failed to repair JSON for resume parsing")
                    raise RuntimeError("Failed to parse JSON response from LLM for resume parsing")
                response = repair_json(response)
                UserInterface.info(f"JSON repair attempt {attempts} for resume parsing.")

    def _prepare_resume_text(self, doc_structure):
        """
        Prepare text content from the document structure for LLM processing.
        """
        text_lines = []
        for para in doc_structure["paragraphs"]:
            text_lines.append(para["text"])
        for table_info in doc_structure["tables"]:
            text_lines.extend(self._get_text_from_table_data(table_info["data"]))
        return '\n'.join(text_lines)

    def _get_text_from_table_data(self, table_data):
        text_lines = []
        for row in table_data:
            for cell in row:
                for para in cell["paragraphs"]:
                    text_lines.append(para["text"])
                for nested_table in cell["tables"]:
                    text_lines.extend(self._get_text_from_table_data(nested_table["data"]))
        return text_lines

    def optimize_resume(self, resume_dict, requirements):
        UserInterface.progress("Optimizing resume sections...")
        UserInterface.info("Incorporating key requirements into resume...")
        prompt = (
            f"Optimize the following resume to highlight the key requirements for a job application.\n\n"
            f"Resume:\n{json.dumps(resume_dict, indent=2, ensure_ascii=False)}\n\n"
            f"Key Requirements:\n- " + '\n- '.join(requirements) + "\n\n"
            "Instructions:\n"
            "1. Review each section of the resume and enhance it by incorporating relevant keywords and phrases from the key requirements.\n"
            "2. Do not remove or summarize any existing content; only add or modify to better match the job requirements.\n"
            "3. Ensure that all original details are preserved exactly as they are.\n"
            "4. Do not include any boolean values; all content should be text.\n"
            "5. Preserve special characters and emojis in the text.\n"
            "6. Ensure the 'Summary' section is a string, not an object.\n"
            "7. Return the optimized resume strictly as valid JSON.\n"
            "Do not include any additional text, explanations, or code block markers."
        )
        response = self.llm.generate(prompt)
        logging.debug(f"LLM Response for resume optimization:\n{response}")

        response = self._clean_json_response(response)

        attempts = 0
        while True:
            try:
                optimized_resume_dict = json.loads(response)
                if attempts > 0:
                    UserInterface.success(f"JSON repair successful after {attempts} attempt(s) for resume optimization.")
                return optimized_resume_dict
            except json.JSONDecodeError as e:
                if attempts == 0:
                    UserInterface.info("Attempting to repair JSON for resume optimization...")
                attempts += 1
                if attempts > 3:
                    logging.error(f"Failed to parse repaired JSON after {attempts} attempts: {e}")
                    UserInterface.error("Failed to repair JSON for resume optimization")
                    raise RuntimeError("Failed to parse JSON response from LLM for resume optimization")
                response = repair_json(response)
                UserInterface.info(f"JSON repair attempt {attempts} for resume optimization.")

    def create_document(self, template_document, optimized_resume_dict, output_path):
        # Create a copy of the template document
        doc = template_document

        # Update the document with optimized content
        self._update_document_with_data(doc, optimized_resume_dict)

        doc.save(output_path)

    def _update_document_with_data(self, document, optimized_resume_dict):
        """
        Update the document with the optimized resume data while preserving the original structure.
        """
        # Map section titles to their corresponding elements
        elements_map = self._map_elements(document)

        for section, content in optimized_resume_dict.items():
            if section in elements_map:
                element_info = elements_map[section]
                self._replace_content_in_element(element_info, content)
            else:
                # If the section does not exist, add it at the end
                document.add_heading(section, level=1)
                self._add_content(document, content)

    def _map_elements(self, document):
        """
        Map section titles to their corresponding elements (paragraphs or table cells).
        """
        elements_map = {}

        # Map from paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if paragraph.style.name.startswith('Heading') or text.isupper():
                elements_map[text] = {
                    "type": "paragraph",
                    "element": paragraph
                }

        # Map from tables
        for table in document.tables:
            self._map_elements_in_table(table, elements_map)

        return elements_map

    def _map_elements_in_table(self, table, elements_map):
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    text = paragraph.text.strip()
                    if paragraph.style.name.startswith('Heading') or text.isupper():
                        elements_map[text] = {
                            "type": "cell",
                            "element": cell
                        }
                for nested_table in cell.tables:
                    self._map_elements_in_table(nested_table, elements_map)

    def _replace_content_in_element(self, element_info, content):
        """
        Replace the text of an element (paragraph or cell) with new content.
        """
        element_type = element_info["type"]
        element = element_info["element"]
        if element_type == "paragraph":
            self._clear_paragraph(element)
            self._add_content(element, content)
        elif element_type == "cell":
            element.text = ''
            self._add_content(element, content)
        else:
            logging.warning(f"Unknown element type: {element_type}")
            UserInterface.warning(f"Unknown element type encountered: {element_type}")

    def _clear_paragraph(self, paragraph):
        """
        Clear the contents of a paragraph.
        """
        p = paragraph._element
        p.clear_content()

    def _add_content(self, container, content):
        if isinstance(content, str):
            paragraphs = content.strip().split('\n')
            for para_text in paragraphs:
                if para_text.strip():
                    if isinstance(container, docx.document.Document):
                        para = container.add_paragraph(para_text.strip())
                        para.style.font.size = Pt(12)
                    elif isinstance(container, docx.text.paragraph.Paragraph):
                        run = container.add_run(para_text.strip())
                        run.font.size = Pt(12)
                    elif isinstance(container, docx.table._Cell):
                        para = container.add_paragraph(para_text.strip())
                        para.style.font.size = Pt(12)
                    else:
                        logging.warning(f"Unknown container type: {type(container)}")
        elif isinstance(content, list):
            for item in content:
                self._add_content(container, item)
        elif isinstance(content, dict):
            for key, value in content.items():
                if isinstance(container, (docx.document.Document, docx.table._Cell)):
                    heading = container.add_paragraph(key)
                    heading.style = 'Heading2'
                    self._add_content(container, value)
                elif isinstance(container, docx.text.paragraph.Paragraph):
                    run = container.add_run(f"{key}:\n")
                    run.font.size = Pt(12)
                    self._add_content(container, value)
                else:
                    logging.warning(f"Unknown container type: {type(container)}")
        elif isinstance(content, bool):
            # Convert boolean to string
            text = str(content)
            if isinstance(container, docx.document.Document):
                para = container.add_paragraph(text)
                para.style.font.size = Pt(12)
            elif isinstance(container, docx.text.paragraph.Paragraph):
                run = container.add_run(text)
                run.font.size = Pt(12)
            elif isinstance(container, docx.table._Cell):
                para = container.add_paragraph(text)
                para.style.font.size = Pt(12)
            else:
                logging.warning(f"Unknown container type: {type(container)}")
        else:
            logging.warning(f"Unknown content type: {type(content)}")
            UserInterface.warning(f"Unknown content type encountered: {type(content)}")

    def _clean_json_response(self, response):
        response = response.strip()
        if response.startswith('```') and response.endswith('```'):
            response = response[3:-3].strip()
        if response.startswith('json'):
            response = response[4:].strip()
        return response
