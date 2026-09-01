import abc
import json
import re
from typing import Any, Dict, Optional, Type
import structlog
from pydantic import BaseModel, ValidationError

from config.settings import settings
from src.llm.rate_limiter import LLMRateLimiter, execute_with_429_retry

logger = structlog.get_logger(__name__)


def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Strip markdown fences, preambles, and postambles to parse clean JSON dict."""
    if not text:
        raise ValueError("Empty response text received from LLM provider")

    cleaned = text.strip()
    # Strip markdown code blocks: ```json ... ``` or ``` ... ```
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = cleaned.replace("```", "").strip()

    # Find first '{' and last '}'
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx : end_idx + 1]

    return json.loads(cleaned)


class LLMProvider(abc.ABC):
    """Abstract interface for multi-tier LLM providers."""

    def __init__(self, name: str, requests_per_minute: int = 60):
        self.name = name
        self.rate_limiter = LLMRateLimiter(name, requests_per_minute=requests_per_minute)

    def build_prompt(self, text: str, schema: Type[BaseModel]) -> str:
        """Construct structured JSON extraction prompt including Pydantic JSON schema."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        return (
            f"You are a high-precision data extraction assistant.\n"
            f"Extract structured information from the following input text matching this JSON schema exactly:\n\n"
            f"JSON SCHEMA:\n{schema_json}\n\n"
            f"INPUT TEXT:\n{text}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"1. Output ONLY raw, valid JSON matching the schema.\n"
            f"2. Do NOT include markdown fences (no ```json), preambles, or explanations.\n"
            f"3. Ensure all required schema fields are present and correctly typed."
        )

    @abc.abstractmethod
    async def extract(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Extract structured JSON matching Pydantic schema from input text."""
        pass


class GeminiProvider(LLMProvider):
    """Tier-1 LLM Provider: Google Gemini 1.5 Flash."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="Gemini-1.5-Flash", requests_per_minute=60)
        self.api_key = api_key or settings.GEMINI_API_KEY

    async def extract(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing")

        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = self.build_prompt(text, schema)
        await self.rate_limiter.acquire()

        async def _call():
            import asyncio
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text

        raw_response = await execute_with_429_retry(_call, self.name)
        json_dict = clean_and_parse_json(raw_response)

        # Validate with Pydantic schema
        validated_model = schema.model_validate(json_dict)
        return validated_model.model_dump(mode="json")


class GroqProvider(LLMProvider):
    """Tier-2 LLM Provider: Groq (Llama-3 70B / 8B)."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "llama3-70b-8192"):
        super().__init__(name="Groq-Llama3", requests_per_minute=60)
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model_name

    async def extract(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing")

        from groq import AsyncGroq
        client = AsyncGroq(api_key=self.api_key)

        prompt = self.build_prompt(text, schema)
        await self.rate_limiter.acquire()

        async def _call():
            completion = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a JSON extraction model. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return completion.choices[0].message.content

        raw_response = await execute_with_429_retry(_call, self.name)
        json_dict = clean_and_parse_json(raw_response)

        # Validate with Pydantic schema
        validated_model = schema.model_validate(json_dict)
        return validated_model.model_dump(mode="json")


class DeepSeekProvider(LLMProvider):
    """Tier-3 Fallback LLM Provider: DeepSeek V3 (OpenAI-compatible API)."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com"):
        super().__init__(name="DeepSeek-V3", requests_per_minute=60)
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url

    async def extract(self, text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is missing")

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        prompt = self.build_prompt(text, schema)
        await self.rate_limiter.acquire()

        async def _call():
            completion = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a JSON extraction model. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return completion.choices[0].message.content

        raw_response = await execute_with_429_retry(_call, self.name)
        json_dict = clean_and_parse_json(raw_response)

        # Validate with Pydantic schema
        validated_model = schema.model_validate(json_dict)
        return validated_model.model_dump(mode="json")
