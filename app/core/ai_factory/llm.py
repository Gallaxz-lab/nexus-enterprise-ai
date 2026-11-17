import time
import random
import hashlib
import logging
from typing import Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel
from google import genai
from google.genai import types
from app.config import settings
from typing import Any, Optional, get_args, get_origin, Union, Literal
from enum import Enum




logger = logging.getLogger(__name__)

class AIFactory:
    """Dynamically routes text and embedding requests to verified cloud model providers."""
    
    @staticmethod
    def _call_gemini_with_retry(
        client: genai.Client,
        prompt: str,
        response_schema: type[BaseModel],
        model_name: str = "gemini-3.8-flash",
        max_retries: int = 4
    ) -> Any:
        """Retries transient 503/429 errors with exponential backoff and jitter."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )
                return response_schema.model_validate_json(response.text)

            except Exception as e:
                last_exception = e
                error_str = str(e)
                is_transient = any(code in error_str for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))

                if is_transient and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Gemini ({model_name}) overloaded (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                    continue
                
                raise e

        raise last_exception

    @staticmethod
    def _call_openai_structured(prompt: str, response_schema: type[BaseModel]) -> Any:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format=response_schema,
        )
        return response.choices[0].message.parsed

    @staticmethod
    def _call_anthropic_structured(prompt: str, response_schema: type[BaseModel]) -> Any:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "structured_output",
                "description": "Output structured JSON matching schema",
                "input_schema": response_schema.model_json_schema()
            }],
            tool_choice={"type": "tool", "name": "structured_output"}
        )
        tool_input = response.content[0].input
        return response_schema.model_validate(tool_input)
    
    @staticmethod
    def _build_mock_value(annotation: Any, field_name: str = "") -> Any:
        """Generate predictable, schema-valid demo values without an API key."""
        origin = get_origin(annotation)
        args = get_args(annotation)
        name = field_name.lower()

        # Handle Optional and Union types (supports both typing.Union and X | Y syntax)
        if origin is Union or getattr(origin, "__name__", "") == "UnionType":
            non_none = [arg for arg in args if arg is not type(None)]
            if not non_none:
                return None
            return AIFactory._build_mock_value(non_none[0], field_name)

        # Handle Literal values
        if origin is Literal:
            return args[0]

        # Handle lists
        if origin is list:
            item_type = args[0] if args else str
            return [AIFactory._build_mock_value(item_type, field_name)]

        # Handle dictionaries
        if origin is dict:
            key_type, value_type = args if len(args) == 2 else (str, str)
            key = AIFactory._build_mock_value(key_type, "key")
            value = AIFactory._build_mock_value(value_type, field_name)
            return {str(key): value}

        # Handle enums
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return list(annotation)[0].value

        # Handle nested Pydantic models
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return AIFactory._build_mock_model(annotation)

        # Generate useful field-specific demo values
        if annotation is str:
            if "email" in name:
                return "demo@example.com"
            if "name" in name:
                return "Demo User"
            if "title" in name:
                return "Demo Analysis"
            if "status" in name:
                return "completed"
            if "category" in name:
                return "General"
            if "summary" in name:
                return "This is a simulated summary generated in demo mode."
            if "answer" in name:
                return "This is a simulated answer. Live AI generation is currently unavailable."
            if "recommendation" in name:
                return "Review the available information and verify before taking action."
            if "message" in name:
                return "Mock mode is active. This response is for demonstration purposes."
            return "Demo response (mock mode)."

        if annotation is bool:
            return True

        if annotation is int:
            return 1

        if annotation is float:
            return 0.95

        return None

    @staticmethod
    def _build_mock_model(response_schema: type[BaseModel]) -> BaseModel:
        """Build a Pydantic-valid mock response using the requested schema."""
        mock_data = {}

        for field_name, field in response_schema.model_fields.items():
            if not field.is_required():
                if field.default_factory is not None:
                    mock_data[field_name] = field.default_factory()
                else:
                    mock_data[field_name] = field.default
            else:
                mock_data[field_name] = AIFactory._build_mock_value(
                    field.annotation,
                    field_name
                )

        return response_schema.model_validate(mock_data)

    @staticmethod
    def _call_mock_structured(
        prompt: str,
        response_schema: type[BaseModel]
    ) -> Any:
        """Return schema-valid simulated data without calling an external AI."""
        logger.warning("Mock AI provider activated. Returning simulated data.")
        return AIFactory._build_mock_model(response_schema)

    @staticmethod
    def generate_structured_json(
        prompt: str, 
        response_schema: type[BaseModel], 
        provider: Optional[str] = None
    ) -> Any:
        """Forces the selected model to return pure data matching a strict Pydantic template."""
        target_provider = provider or settings.DEFAULT_LLM_PROVIDER

        if target_provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise HTTPException(status_code=500, detail="OpenAI API key missing.")
            try:
                return AIFactory._call_openai_structured(prompt, response_schema)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"OpenAI SDK Error: {str(e)}")
        
        elif target_provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(status_code=500, detail="Gemini API key missing.")
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                return AIFactory._call_gemini_with_retry(
                    client=client,
                    prompt=prompt,
                    response_schema=response_schema,
                    model_name="gemini-3.8-flash"
                )
            except Exception as gemini_err:
                error_str = str(gemini_err)
                is_overload = any(code in error_str for code in ("503", "UNAVAILABLE", "429"))

                # Automatic cross-provider fallback if Gemini is overloaded and another key exists
                if is_overload and settings.OPENAI_API_KEY:
                    logger.warning("Gemini overloaded after retries. Falling back to OpenAI.")
                    try:
                        return AIFactory._call_openai_structured(prompt, response_schema)
                    except Exception as openai_err:
                        logger.error(f"OpenAI fallback also failed: {openai_err}")

                if is_overload and settings.ANTHROPIC_API_KEY:
                    logger.warning("Gemini overloaded after retries. Falling back to Anthropic.")
                    try:
                        return AIFactory._call_anthropic_structured(prompt, response_schema)
                    except Exception as anthropic_err:
                        logger.error(f"Anthropic fallback also failed: {anthropic_err}")

                status_code = 503 if is_overload else 502
                raise HTTPException(status_code=status_code, detail=f"Gemini SDK Error: {error_str}")

        elif target_provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise HTTPException(status_code=500, detail="Anthropic API key missing.")
            try:
                return AIFactory._call_anthropic_structured(prompt, response_schema)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Anthropic SDK Error: {str(e)}")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI Provider '{target_provider}' is unrecognized or unmapped."
            )

    @staticmethod
    def generate_embedding(text_content: str, provider: Optional[str] = None) -> list[float]:
        """Dynamically interfaces with the active cloud provider to return a 1536-dim vector."""
        target_provider = provider or settings.DEFAULT_LLM_PROVIDER
        
        normalized_text = text_content.replace("\n", " ").strip()
        if not normalized_text:
            return [0.0] * 1536
            
        try:
            if target_provider == "openai":
                if not settings.OPENAI_API_KEY:
                    raise ValueError("OpenAI key missing")
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.embeddings.create(
                    input=[normalized_text],
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
                
            elif target_provider == "gemini":
                if not settings.GEMINI_API_KEY:
                    raise ValueError("Gemini key missing")
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=normalized_text,
                    config=types.EmbedContentConfig(output_dimensionality=1536)
                )
                return response.embeddings[0].values
                
            else:
                raise ValueError(f"Provider '{target_provider}' routed to local deterministic engine.")
                
        except Exception as e:
            logger.warning(f"Embedding API failed ({e}). Falling back to deterministic MD5 vector.")
            hash_bytes = hashlib.md5(normalized_text.encode('utf-8')).digest()
            
            base_vector = []
            for i in range(1536):
                byte_idx = (i * 7) % len(hash_bytes)
                bit_idx = (i * 3) % 8
                bit_signal = (hash_bytes[byte_idx] >> bit_idx) & 1
                
                char_weight = ord(normalized_text[i % len(normalized_text)]) if normalized_text else 0
                val = (bit_signal * 0.5) + ((char_weight % 10) * 0.05)
                base_vector.append(val)
        
            magnitude = sum(x**2 for x in base_vector) ** 0.5 or 1.0
            return [float(x / magnitude) for x in base_vector]
