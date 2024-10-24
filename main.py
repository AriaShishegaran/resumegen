import sys
import logging

from user_interface import UserInterface
from llm_client import OllamaClient
from job_processor import JobProcessor
from resume_processor import ResumeProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler("debug.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
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

        # Process resume
        UserInterface.progress("Loading resume template...")
        resume_document, doc_structure = resume_processor.load_template(template_path)
        UserInterface.success("Resume template loaded")

        # Parse resume
        UserInterface.progress("Parsing resume...")
        resume_dict = resume_processor.parse_resume(doc_structure)
        UserInterface.success("Resume parsed")

        # Optimize resume
        UserInterface.progress("Optimizing resume...")
        optimized_resume_dict = resume_processor.optimize_resume(resume_dict, requirements)
        UserInterface.success("Resume optimized")

        # Create document
        UserInterface.progress("Creating ATS-friendly document...")
        output_path = "ATS_Resume.docx"
        resume_processor.create_document(resume_document, optimized_resume_dict, output_path)
        UserInterface.success(f"Resume saved as: {output_path}")

    except Exception as e:
        UserInterface.error(str(e))
        logging.error(f"Detailed error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
