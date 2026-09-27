import os
import hashlib
from typing import Any, Dict
from fastapi import HTTPException, status
from pydantic import BaseModel
from app.config import settings
from google import genai
from google.genai import types

class AIFactory:
    """Dynamically routes text requests to verified cloud model providers."""
    
    @staticmethod
    def generate_structured_json(prompt: str, response_schema: type[BaseModel], provider: str = None) -> Any:
        """Forces the selected model to return pure data matching a strict Pydantic template."""
        target_provider = provider or settings.DEFAULT_LLM_PROVIDER

        if target_provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise HTTPException(status_code=500, detail="OpenAI API key missing.")
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format=response_schema,
            )
            return response.choices[0].message.parsed
        
        elif target_provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(status_code=500, detail="Gemini API key missing.")
    
   
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash", 
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,  
                    ),
                )
                return response_schema.model_validate_json(response.text)
            
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Gemini SDK Error: {str(e)}")


        elif target_provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise HTTPException(status_code=500, detail="Anthropic API key missing.")
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            # Anthropic handles structural outputs via built-in tool utilities
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

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI Provider '{target_provider}' is unrecognized or unmapped."
            )
    @staticmethod
    def generate_embedding(text_content: str, provider: str = None) -> list[float]:
        """Dynamically interfaces with the active cloud provider to return a vector representation."""
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
                return response.data.embedding
                
            elif target_provider == "gemini":
                if not settings.GEMINI_API_KEY:
                    raise ValueError("Gemini key missing")
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=normalized_text
                )
                return response['embedding']
                
            else:
                raise ValueError("Route directly to local deterministic signature engine.")
                
        except Exception:
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