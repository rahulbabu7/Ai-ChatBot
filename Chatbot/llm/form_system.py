"""
Form Collection System for RAG Chatbot
Handles multi-turn data collection for actions like booking demos, registration, etc.
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class FormStatus(Enum):
    """Form completion status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FieldType(Enum):
    """Supported field types with validation"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    CHOICE = "choice"
    NUMBER = "number"


class FormField:
    """Individual form field with validation"""

    def __init__(
        self,
        name: str,
        field_type: FieldType,
        prompt: str,
        required: bool = True,
        validation_pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        description: Optional[str] = None
    ):
        self.name = name
        self.field_type = field_type
        self.prompt = prompt
        self.required = required
        self.validation_pattern = validation_pattern
        self.choices = choices
        self.description = description

    def validate(self, value: str) -> tuple:
        """Validate field value, return (is_valid, error_message)"""
        if not value or not value.strip():
            if self.required:
                return False, f"{self.name} is required"
            return True, None

        value = value.strip()

        # Email validation
        if self.field_type == FieldType.EMAIL:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, "Please provide a valid email address (e.g., name@example.com)"

        # Phone validation
        elif self.field_type == FieldType.PHONE:
            phone_clean = re.sub(r'[\s\-\(\)\.]+', '', value)
            if not re.match(r'^\+?[0-9]{10,15}$', phone_clean):
                return False, "Please provide a valid phone number (10-15 digits)"

        # Number validation
        elif self.field_type == FieldType.NUMBER:
            try:
                float(value)
            except ValueError:
                return False, "Please provide a valid number"

        # Choice validation
        elif self.field_type == FieldType.CHOICE and self.choices:
            if value.lower() not in [c.lower() for c in self.choices]:
                return False, f"Please choose from: {', '.join(self.choices)}"

        # Custom pattern validation
        if self.validation_pattern:
            if not re.match(self.validation_pattern, value):
                return False, f"Invalid format for {self.name}"

        return True, None


class FormTemplate:
    """Template for different form types"""

    def __init__(self, form_type: str, fields: List[FormField], success_message: str):
        self.form_type = form_type
        self.fields = fields
        self.success_message = success_message

    @staticmethod
    def get_demo_booking_form():
        """Standard demo booking form"""
        return FormTemplate(
            form_type="demo_booking",
            fields=[
                FormField("name", FieldType.TEXT, "What's your full name?", required=True),
                FormField("email", FieldType.EMAIL, "What's your email address?", required=True),
                FormField("phone", FieldType.PHONE, "What's your phone number?", required=False,
                         description="We'll use this to schedule your demo"),
                FormField("company", FieldType.TEXT, "What company are you with?", required=False),
                FormField("preferred_time", FieldType.CHOICE,
                         "When would you prefer the demo?",
                         choices=["morning", "afternoon", "evening"], required=False)
            ],
            success_message="✅ Thank you! We've received your demo request. Our team will contact you shortly at {email}."
        )

    @staticmethod
    def get_contact_form():
        """General contact form with phone number (REQUIRED)"""
        return FormTemplate(
            form_type="contact",
            fields=[
                FormField("name", FieldType.TEXT, "What's your name?", required=True),
                FormField("email", FieldType.EMAIL, "What's your email?", required=True),
                FormField("phone", FieldType.PHONE, "What's your phone number?", required=True),  # ← required=True
                FormField("message", FieldType.TEXT, "What would you like to discuss?", required=True)
            ],
            success_message="✅ Thanks {name}! We've received your message and will get back to you at {email} soon."
        )


class FormCollector:
    """Manages form collection state"""

    def __init__(self, template: FormTemplate):
        self.template = template
        self.status = FormStatus.NOT_STARTED
        self.collected_data: Dict[str, str] = {}
        self.current_field_index = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def start(self) -> str:
        """Start form collection"""
        self.status = FormStatus.IN_PROGRESS
        self.started_at = datetime.now()
        return self._get_next_prompt()

    def process_response(self, user_input: str) -> Dict[str, Any]:
        """Process user response"""

        # Check for cancellation
        cancel_keywords = ['cancel', 'stop', 'quit', 'nevermind', 'never mind', 'exit']
        if any(keyword in user_input.lower() for keyword in cancel_keywords):
            self.status = FormStatus.CANCELLED
            return {
                "status": "cancelled",
                "message": "No problem! Let me know if you'd like to try again later.",
                "form_complete": False
            }

        # Check for skip on optional fields
        if user_input.lower().strip() in ['skip', 'pass', 'next']:
            current_field = self.template.fields[self.current_field_index]
            if not current_field.required:
                self.collected_data[current_field.name] = ""
                self.current_field_index += 1

                if self.current_field_index >= len(self.template.fields):
                    return self._complete_form()

                return {
                    "status": "in_progress",
                    "message": self._get_next_prompt(),
                    "field": self.template.fields[self.current_field_index].name,
                    "form_complete": False,
                    "progress": f"{self.current_field_index}/{len(self.template.fields)}"
                }

        # Get current field
        if self.current_field_index >= len(self.template.fields):
            return self._complete_form()

        current_field = self.template.fields[self.current_field_index]

        # Extract value
        extracted_value = self._extract_value(user_input, current_field)

        # Validate
        is_valid, error_message = current_field.validate(extracted_value)

        if not is_valid:
            return {
                "status": "validation_error",
                "message": f"❌ {error_message}\n\n{current_field.prompt}",
                "field": current_field.name,
                "form_complete": False
            }

        # Store value
        self.collected_data[current_field.name] = extracted_value
        self.current_field_index += 1

        # Check completion
        if self.current_field_index >= len(self.template.fields):
            return self._complete_form()

        # Get next prompt
        return {
            "status": "in_progress",
            "message": self._get_next_prompt(),
            "field": self.template.fields[self.current_field_index].name,
            "form_complete": False,
            "progress": f"{self.current_field_index}/{len(self.template.fields)}"
        }

    def _extract_value(self, user_input: str, field: FormField) -> str:
        """Extract relevant value from input"""
        user_input = user_input.strip()

        # Email extraction
        if field.field_type == FieldType.EMAIL:
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_input)
            if email_match:
                return email_match.group(0)

        # Phone extraction
        elif field.field_type == FieldType.PHONE:
            phone_match = re.search(r'[\d\s\-\(\)\.+]{10,}', user_input)
            if phone_match:
                return phone_match.group(0)

        # Choice matching
        elif field.field_type == FieldType.CHOICE and field.choices:
            user_lower = user_input.lower()
            for choice in field.choices:
                if choice.lower() in user_lower:
                    return choice

        return user_input

    def _get_next_prompt(self) -> str:
        """Get prompt for next field"""
        if self.current_field_index >= len(self.template.fields):
            return ""

        field = self.template.fields[self.current_field_index]
        prompt = field.prompt

        if field.description:
            prompt += f"\n💡 {field.description}"

        if field.choices:
            prompt += f"\nOptions: {', '.join(field.choices)}"

        if not field.required:
            prompt += "\n(Optional - type 'skip' to leave blank)"

        return prompt

    def _complete_form(self) -> Dict[str, Any]:
        """Complete form"""
        self.status = FormStatus.COMPLETED
        self.completed_at = datetime.now()

        # Format success message
        success_msg = self.template.success_message
        for key, value in self.collected_data.items():
            success_msg = success_msg.replace(f"{{{key}}}", value)

        return {
            "status": "completed",
            "message": success_msg,
            "form_complete": True,
            "collected_data": self.collected_data,
            "form_type": self.template.form_type
        }
