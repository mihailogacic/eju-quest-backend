"""
lesson_services.py

This module provides the LessonServices class, responsible for generating structured 
lesson content using OpenAI's GPT-4 API. """

import json
import openai
from django.conf import settings


class LessonServices:
    """
    A service class responsible for generating lesson content using OpenAI's GPT-4 API.

    This class interacts with OpenAI's API to generate structured educational content,
    including lesson details and multiple-choice quizzes based on a given topic, age level,
    and lesson length.
    """

    @staticmethod
    def generate_new_content(data):
        """
        Generates a new lesson using OpenAI and returns structured lesson data.

        This method constructs a prompt tailored for OpenAI's GPT-4 API to generate educational 
        content in JSON format. The generated content includes lesson details and a quiz 
        with multiple-choice questions.
        """

        topic = data.get("title")
        age = data.get("age_level")
        lesson_length = data.get("lesson_length")

        # Ensure required data is present
        if not topic or not age or not lesson_length:
            raise ValueError(
                "Missing required fields: title, age_level, or lesson_length.")

        # OpenAI API Key
        client = openai.OpenAI(api_key=settings.OPEN_AI_API_KEY)

        # Prompt for generating lesson content
        prompt = (
            f"Teach about {topic} in an engaging, detailed way suitable for a child of age {age}. "
            f"Provide a {lesson_length} lesson with at least 5 distinct sections,"
            f"each containing multiple  paragraphs or several sentences."
            f"Avoid using Markdown or asterisks for bold/italics. "
            f"Make headings in ALL CAPS, and provide ample detail, including historical background,"
            f"major figures or artists, cultural impact, current trends, technology, \
                and future directions.\n\n"
            f"After that, create a 5-question multiple-choice quiz about {topic}, \
                each with options A), B), C), D). "
            f"At the end of each question, indicate the correct answer in the format: \
                'Answer: X'.\n\n"
            f"Do not include any disclaimers or extra text beyond the lesson and quiz."
            "Return me a JSON response. It should be following format: \
            {'content': [{'heading': 'heading of the paragraph' 'text':'text of the paragraph'}], \
            'questions': [{'question': 'quesetion_text', \
            'options': [{'option': 'A', 'text': 'option_text'}], 'answer': 'answer_option' }]}"
        )

        # OpenAI API call
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system",
                    "content": "You'r expert in educational content generation."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract text response from OpenAI
        text_response = response.choices[0].message.content.strip()
        json_object = json.loads(text_response)
        return json_object

    @staticmethod
    def parse_remaining_time(rt):
        """
        Prima:
        • int  → sekunde           (npr. 47)
        • str  → 'mm:ss'           ('02:15')
        • int  → milisekunde ≥1000 (32000)
        Vraća int sekunde ili None.
        """
        if rt is None:
            return None
        try:
            rt = int(rt)
            if rt >= 1000:
                return rt // 1000
            return rt
        except ValueError:
            pass

        if isinstance(rt, str) and ":" in rt:
            m, s = rt.split(":")
            return int(m) * 60 + int(s)
        return None
