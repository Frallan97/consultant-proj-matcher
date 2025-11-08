"""
Resume PDF parsing service using OpenAI API.
Extracts structured data from PDF resumes.
"""
import os
import json
import base64
import random
from io import BytesIO
from typing import List
from pdf2image import convert_from_bytes
from openai import OpenAI
from openai import OpenAIError
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import ConsultantData
from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

# Common first and last names for generating realistic names
FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
    "Blake", "Cameron", "Dakota", "Drew", "Emery", "Finley", "Harper", "Hayden",
    "Jamie", "Kai", "Logan", "Micah", "Noah", "Parker", "Peyton", "Reese",
    "River", "Rowan", "Sage", "Skylar", "Tatum", "Tyler", "Zion"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen",
    "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter",
    "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz",
    "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy", "Cook"
]


def generate_random_name() -> str:
    """
    Generate a random realistic name.
    
    Returns:
        A random first name + last name combination with an asterisk (*) appended
    """
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    return f"{first_name} {last_name}*"


def parse_resume_pdf(pdf_bytes: bytes) -> ConsultantData:
    """
    Parse PDF resume and extract structured data using OpenAI API.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        ConsultantData instance with parsed resume data
        
    Raises:
        Exception if parsing fails
    """
    api_key = os.getenv("OPENAI_APIKEY")
    if not api_key:
        # Missing API key is a server configuration error, not a client error
        raise RuntimeError("OPENAI_APIKEY not found in environment variables")
    
    client = OpenAI(api_key=api_key)
    
    # Convert PDF pages to images
    try:
        images = convert_from_bytes(pdf_bytes)
        if not images:
            raise ValueError("Failed to convert PDF to images")
    except Exception as e:
        raise ValueError(f"Error converting PDF to images: {str(e)}")
    
    # Convert first page to base64 (resumes are typically single page or we can process multiple pages)
    # For now, process first page. Can be extended to process all pages if needed
    image_bytes = BytesIO()
    images[0].save(image_bytes, format='PNG')
    image_base64 = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
    
    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured information from resumes. Extract the following fields: name, email, phone, skills (as array of strings), experience (as text summary), education (as text summary). Return JSON only with these exact field names."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract structured information from this resume. Return JSON with fields: name (string), email (string, can be empty), phone (string, can be empty), skills (array of strings), experience (text summary), education (text summary). Ensure all fields are present in the response."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse response
        if not response.choices or len(response.choices) == 0:
            raise ValueError("OpenAI API returned no choices in response")
        
        choice = response.choices[0]
        message = choice.message
        content = message.content
        
        # Check finish_reason to understand why content might be None
        finish_reason = getattr(choice, 'finish_reason', None)
        if finish_reason:
            if finish_reason == "content_filter":
                raise ValueError("OpenAI API filtered the response content due to content policy")
            elif finish_reason == "length":
                raise ValueError("OpenAI API response was truncated due to length limits")
            elif finish_reason == "stop" and content is None:
                raise ValueError("OpenAI API returned None content with stop finish_reason")
        
        if content is None:
            raise ValueError(f"OpenAI API returned None content. Finish reason: {finish_reason}")
        
        if not isinstance(content, str):
            raise ValueError(f"OpenAI API returned unexpected content type: {type(content)}")
        
        if not content.strip():
            raise ValueError("OpenAI API returned empty content string")
        
        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse OpenAI response as JSON. Content: {content[:200]}... Error: {str(e)}")
        
        # Extract fields and ensure they match ConsultantData structure
        name = parsed_data.get("name", "").strip()
        email = parsed_data.get("email", "").strip()
        phone = parsed_data.get("phone", "").strip()
        skills = parsed_data.get("skills", [])
        if isinstance(skills, str):
            # Handle case where skills might be a string
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif not isinstance(skills, list):
            skills = []
        else:
            skills = [str(s).strip() for s in skills if s]

        experience = parsed_data.get("experience", "").strip()
        education = parsed_data.get("education", "").strip()
        
        # If name is missing or empty, generate a random realistic name with asterisk
        if not name:
            name = generate_random_name()
        
        # Create and return ConsultantData instance
        return ConsultantData(
            name=name,
            email=email,
            phone=phone,
            skills=skills,
            experience=experience,
            education=education,
            availability="available"
        )
        
    except ValueError as e:
        # Re-raise ValueError as-is (already formatted)
        raise
    except OpenAIError as e:
        # Log the full error for debugging
        logger.error("OpenAI API error during resume parsing", exc_info=True)
        # Raise RuntimeError for OpenAI errors so they get caught as 500 in main.py
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        # Let other exceptions bubble up (will be caught as 500 in main.py)
        logger.error("Unexpected error during resume parsing", exc_info=True)
        raise
