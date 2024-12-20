# main.py

import sys
import logging

from user_interface import UserInterface
from llm_client import ModelClientFactory
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

        # Prompt the user to select the model server
        UserInterface.info("Select the LLM server:")
        UserInterface.info("1. LMStudio")
        UserInterface.info("2. Ollama")
        selection = input("Enter 1 or 2: ").strip()
        if selection == '1':
            client_type = 'lmstudio'
            # Prompt for model name and identifier
            model_path = input("Enter the LMStudio model path (e.g., 'mlx-community/Llama-3.2-3B-Instruct-4bit'): ").strip()
            model_identifier = input("Enter the model identifier (e.g., 'llama-3.2-3b-instruct'): ").strip()
            # Optionally prompt for host and port
            host = input("Enter the LMStudio host (default 'localhost'): ").strip() or 'localhost'
            port_input = input("Enter the LMStudio port (default '1234'): ").strip()
            port = int(port_input) if port_input else 1234
            llm = ModelClientFactory.create_client(client_type=client_type, model=model_identifier, host=host, port=port, model_path=model_path)
        elif selection == '2':
            client_type = 'ollama'
            # Optionally prompt for model name
            model_name = input("Enter the Ollama model name (e.g., 'llama3.2'): ").strip()
            llm = ModelClientFactory.create_client(client_type=client_type, model=model_name)
        else:
            UserInterface.error("Invalid selection. Please enter 1 or 2.")
            sys.exit(1)

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
