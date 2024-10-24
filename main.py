# main.py

import sys
import logging

from user_interface import UserInterface
from llm_client import OllamaClient
from job_processor import JobProcessor
from resume_processor import ResumeProcessor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture detailed logs
    format='%(message)s',
    handlers=[
        logging.FileHandler("debug.log", encoding='utf-8'),
    ]
)

def main():
    try:
        if len(sys.argv) != 3:
            UserInterface.error("Usage: python script.py <template.docx> <job_url>")
            sys.exit(1)

        template_path, job_url = sys.argv[1], sys.argv[2]

        # Initialize components
        llm = OllamaClient()
        job_processor = JobProcessor(llm)
        resume_processor = ResumeProcessor(llm)

        # Process job posting
        UserInterface.progress("Analyzing job posting...")
        job_title, job_description = job_processor.fetch_and_parse(job_url)
        UserInterface.success("Job posting analyzed")

        # Extract requirements
        UserInterface.progress("Extracting requirements...")
        requirements = job_processor.extract_requirements(job_description)
        UserInterface.success(f"Found {len(requirements)} key requirements")

        # Print key requirements
        UserInterface.print_requirements(requirements)

        # Load the template
        UserInterface.progress("Loading resume template...")
        resume_document = resume_processor.load_template(template_path)
        UserInterface.success("Resume template loaded")

        # Process the document
        UserInterface.progress("Processing resume...")
        resume_processor.process_document(resume_document, requirements)
        UserInterface.success("Resume processed")

        # Save the document
        UserInterface.progress("Saving optimized resume...")
        output_path = "ATS_Resume.docx"
        resume_processor.save_document(resume_document, output_path)

    except Exception as e:
        UserInterface.error(str(e))
        logging.error(f"Detailed error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
