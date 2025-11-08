"""
Service for chat functionality with OpenAI.
"""
import os
import json
from typing import Optional, List
from openai import OpenAI
from models import ChatMessage, RoleQuery, ChatResponse


class ChatService:
    """Service for handling chat interactions with OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_APIKEY")
        if not self.api_key:
            raise ValueError("OPENAI_APIKEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.api_key)
        self.system_prompt = """You are a helpful assistant helping assemble a development team. 
Your goal is to quickly understand project requirements and generate a team FAST.

URGENCY DETECTION:
- If the user mentions being in a hurry, urgent, ASAP, quickly, fast, or any time pressure - generate roles IMMEDIATELY with zero questions
- If the user provides ANY project description, generate roles immediately - don't ask questions
- Only ask questions if the message is completely empty or just "hello" with no context

Be extremely proactive and make reasonable assumptions. Generate roles on the FIRST message if possible.

Guidelines:
- If the user mentions a project type (web app, mobile app, game, API, etc.), generate appropriate roles IMMEDIATELY
- Make reasonable assumptions about tech stack based on project type if not specified
- For web apps, typically include: Frontend Engineer, Backend Engineer (and optionally Full-stack, DevOps, Designer)
- For mobile apps, typically include: Mobile Developer (iOS/Android), Backend Engineer
- For games, typically include: Game Developer, Backend Engineer, Designer
- For APIs/backend services: Backend Engineer, DevOps Engineer
- For data/ML projects: Data Engineer, ML Engineer, Backend Engineer
- Default to common modern stacks (React, Node.js, Python, etc.) if not specified

Generate structured role queries in JSON format. The JSON should be embedded in your response like this:

<roles>
{
  "roles": [
    {
      "title": "Frontend Engineer",
      "description": "Description of what this role needs",
      "query": "Vector search query for matching candidates (e.g., 'Frontend developer with React and TypeScript experience')",
      "requiredSkills": ["React", "TypeScript"]
    }
  ]
}
</roles>

CRITICAL: Generate roles IMMEDIATELY when you detect urgency or when the user provides any project information. 
Don't ask questions - be decisive and helpful. Speed is more important than perfect information."""
    
    def process_chat(self, messages: List[ChatMessage]) -> ChatResponse:
        """Process chat messages and return response with optional roles."""
        try:
            # Prepare messages for OpenAI
            openai_messages = [{"role": "system", "content": self.system_prompt}]
            for msg in messages:
                openai_messages.append({"role": msg.role, "content": msg.content})
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=openai_messages,
                temperature=0.7
            )
            
            if not response.choices or len(response.choices) == 0:
                raise ValueError("OpenAI API returned no choices")
            
            content = response.choices[0].message.content
            
            # Check if response contains role queries
            is_complete = False
            roles = None
            
            if "<roles>" in content and "</roles>" in content:
                try:
                    roles_start = content.find("<roles>") + len("<roles>")
                    roles_end = content.find("</roles>")
                    roles_json = content[roles_start:roles_end].strip()
                    roles_data = json.loads(roles_json)
                    roles = [RoleQuery(**role) for role in roles_data.get("roles", [])]
                    is_complete = True
                    # Remove the roles tag from the content
                    content = content[:content.find("<roles>")].strip() + content[content.find("</roles>") + len("</roles>"):].strip()
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error parsing roles from OpenAI response: {e}")
                    # Continue without roles
            
            return ChatResponse(
                role="assistant",
                content=content,
                isComplete=is_complete,
                roles=roles
            )
        
        except Exception as e:
            print(f"Error in chat service: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error processing chat: {str(e)}")

