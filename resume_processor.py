# resume_processor.py

import logging
import docx
from docx.shared import Pt
from user_interface import UserInterface
from requests.exceptions import RequestException
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console

console = Console()

class ResumeProcessor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def load_template(self, file_path):
        try:
            document = docx.Document(file_path)
            return document
        except Exception as e:
            logging.error(f"Failed to load resume template: {str(e)}")
            raise RuntimeError(f"Failed to load resume template: {str(e)}")

    def process_document(self, document, requirements):
        UserInterface.progress("Optimizing resume sections...")
        UserInterface.info("Incorporating key requirements into resume sections...")

        total_sections = self._count_sections(document)
        current_section = 0

        # Define a consistent system message for all sections
        system_message = (
            "You are an expert resume optimizer. Ensure that all responses are accurate, factual, "
            "and adhere strictly to the instructions provided. Do not include any information that "
            "is not present in the input. Your goal is to enhance the resume sections by incorporating "
            "relevant keywords from the key requirements."
        )

        with Progress(
            "[progress.description]{task.description}",
            SpinnerColumn(),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Processing sections...", total=total_sections)

            # Process paragraphs
            for paragraph in document.paragraphs:
                original_text = paragraph.text.strip()
                if original_text:
                    current_section += 1
                    UserInterface.section_status(current_section, total_sections, "paragraph")
                    try:
                        adjusted_text = self.optimize_section(original_text, requirements, system_message)
                        paragraph.text = adjusted_text
                        UserInterface.success(f"Section {current_section}/{total_sections} optimized successfully")
                    except Exception as e:
                        logging.error(f"Error processing paragraph {current_section}: {str(e)}")
                        UserInterface.error(f"Error processing paragraph {current_section}: {str(e)}")
                    progress.update(task, advance=1)

            # Process tables
            for table in document.tables:
                current_section = self._process_table(table, requirements, current_section, total_sections, system_message, progress, task)

    def _process_table(self, table, requirements, current_section, total_sections, system_message, progress, task):
        for row in table.rows:
            for cell in row.cells:
                # Process paragraphs in the cell
                for paragraph in cell.paragraphs:
                    original_text = paragraph.text.strip()
                    if original_text:
                        current_section += 1
                        UserInterface.section_status(current_section, total_sections, "table cell")
                        try:
                            adjusted_text = self.optimize_section(original_text, requirements, system_message)
                            paragraph.text = adjusted_text
                            UserInterface.success(f"Section {current_section}/{total_sections} optimized successfully")
                        except Exception as e:
                            logging.error(f"Error processing table cell {current_section}: {str(e)}")
                            UserInterface.error(f"Error processing table cell {current_section}: {str(e)}")
                        progress.update(task, advance=1)
                # Process nested tables
                for nested_table in cell.tables:
                    current_section = self._process_table(nested_table, requirements, current_section, total_sections, system_message, progress, task)
        return current_section

    def optimize_section(self, content, requirements, system_message):
        # Prepare the prompt
        prompt = (
            f"Resume Section:\n{content}\n\n"
            f"Key Requirements:\n- " + '\n- '.join(requirements) + "\n\n"
            "Instructions:\n"
            "1. Review the section and enhance it by incorporating relevant keywords and phrases from the key requirements.\n"
            "2. Do not remove or summarize any existing content; only add or modify to better match the job requirements.\n"
            "3. Ensure that all original details are preserved exactly as they are.\n"
            "4. Do not include any boolean values; all content should be text.\n"
            "5. Preserve special characters and emojis in the text.\n"
            "6. Return the optimized section as plain text.\n"
            "Do not include any additional text, explanations, or code block markers."
        )

        try:
            response = self.llm.generate(prompt, system_message)
            logging.debug(f"LLM Response for section optimization:\n{response}")

            adjusted_content = self._clean_response(response)
            return adjusted_content
        except Exception as e:
            logging.error(f"Exception in optimize_section: {str(e)}")
            raise RuntimeError(f"Failed to optimize section: {str(e)}")

    def _clean_response(self, response):
        response = response.strip()
        if response.startswith('```') and response.endswith('```'):
            response = response[3:-3].strip()
        if response.startswith('text'):
            response = response[4:].strip()
        return response

    def save_document(self, document, output_path):
        try:
            document.save(output_path)
            UserInterface.success(f"Resume saved as: {output_path}")
        except Exception as e:
            logging.error(f"Failed to save document: {str(e)}")
            raise RuntimeError(f"Failed to save document: {str(e)}")

    def _count_sections(self, document):
        count = 0
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                count += 1
        for table in document.tables:
            count += self._count_sections_in_table(table)
        return count

    def _count_sections_in_table(self, table):
        count = 0
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if paragraph.text.strip():
                        count += 1
                for nested_table in cell.tables:
                    count += self._count_sections_in_table(nested_table)
        return count
