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

logger = logging.getLogger(__name__)

class AIFactory:
    """Dynamically routes text and embedding requests to verified cloud model providers."""
    
    VITALFORM_PRODUCTS = [
        {
            "sku": "VF-T100",
            "name_th": "ลู่วิ่งไฟฟ้า RUNFORM T100",
            "name_en": "RUNFORM T100 Treadmill",
            "category": "fitness_equipment",
            "price_thb": 12900,
            "specifications": {
                "motor": "2.0 CHP (demo rating)",
                "speed_kmh": "1-14",
                "incline": "Manual 3-level incline",
                "running_surface_cm": "42 x 120",
                "max_user_weight_kg": 110,
                "foldable": True,
                "programs": 12,
                "dimensions_cm": "160 x 72 x 128",
                "net_weight_kg": 48,
                "warranty_demo": "Frame 1 year; motor 1 year; parts 6 months"
            }
        },
        {
            "sku": "VF-R20",
            "name_th": "จักรยานออกกำลังกาย SPIN R20",
            "name_en": "SPIN R20 Exercise Bike",
            "category": "fitness_equipment",
            "price_thb": 7900,
            "specifications": {
                "resistance": "8-level manual magnetic",
                "flywheel_kg": 6,
                "seat": "4-way adjustable",
                "max_user_weight_kg": 100,
                "dimensions_cm": "96 x 51 x 118",
                "net_weight_kg": 25,
                "warranty_demo": "Frame 1 year; parts 6 months"
            }
        },
        {
            "sku": "VF-D50",
            "name_th": "ชุดดัมเบลปรับน้ำหนัก V-CORE D50",
            "name_en": "V-CORE D50 Adjustable Dumbbell Set",
            "category": "fitness_equipment",
            "price_thb": 2490,
            "specifications": {
                "weight_per_dumbbell_kg": "2.5-10",
                "increment_kg": 2.5,
                "max_combined_weight_kg": 20,
                "material": "Steel core with polymer-coated plates",
                "warranty_demo": "6 months"
            }
        },
        {
            "sku": "VF-BP01",
            "name_th": "เครื่องวัดความดันโลหิต CARE BP01",
            "name_en": "CARE BP01 Upper-arm Blood Pressure Monitor",
            "category": "healthcare",
            "price_thb": 1290,
            "specifications": {
                "measurement": "Upper-arm oscillometric (demo description)",
                "cuff_range_cm": "22-32",
                "memory": "2 users x 60 readings",
                "display": "LCD",
                "power": "4 AA batteries or optional USB",
                "warranty_demo": "1 year",
                "safety_note": "Demo information only; not medical diagnosis"
            }
        },
        {
            "sku": "VF-S10",
            "name_th": "เครื่องชั่งน้ำหนักดิจิทัล BALANCE S10",
            "name_en": "BALANCE S10 Digital Scale",
            "category": "healthcare",
            "price_thb": 890,
            "specifications": {
                "capacity_kg": 180,
                "graduation_kg": 0.1,
                "display": "LCD",
                "power": "2 AAA batteries",
                "warranty_demo": "6 months"
            }
        }
    ]

    @staticmethod
    def _find_vitalform_products(prompt: str) -> list[dict]:
        """Find products mentioned in a customer question."""
        query = prompt.lower()
        matches = []

        for product in AIFactory.VITALFORM_PRODUCTS:
            searchable = [
                product["sku"],
                product["name_th"],
                product["name_en"],
                product["category"],
            ]

            if any(term.lower() in query for term in searchable):
                matches.append(product)

        # If the question asks about all products or comparisons,
        # return the full catalog.
        all_keywords = (
            "ทั้งหมด", "all products", "ทุกสินค้า",
            "เปรียบเทียบ", "compare", "comparison",
            "รายการสินค้า", "catalog", "สินค้าอะไร"
        )

        if any(keyword in query for keyword in all_keywords):
            return AIFactory.VITALFORM_PRODUCTS

        return matches

    @staticmethod
    def _build_mock_answer(prompt: str, products: list[dict]) -> str:
        """Create a factual customer-facing answer from the local catalog."""
        disclaimer = (
            "หมายเหตุ: นี่คือคำตอบจาก Mock Provider "
            "โดยใช้ข้อมูลสินค้าสมมติสำหรับ Demo เท่านั้น "
            "ไม่ใช่ข้อมูลหรือคำยืนยันจากผู้ผลิตจริง"
        )

        if not products:
            return (
                "ขออภัย ขณะนี้ Mock Provider ยังไม่มีข้อมูลที่ตรงกับคำถามนี้ "
                "กรุณาระบุชื่อสินค้า หรือ SKU ที่ต้องการสอบถาม "
                "และโปรดติดต่อเจ้าหน้าที่เพื่อยืนยันข้อมูลเพิ่มเติม\n\n"
                + disclaimer
            )

        lines = []

        for product in products:
            lines.append(
                f"{product['name_th']} ({product['name_en']})\n"
                f"SKU: {product['sku']}\n"
                f"ราคา: {product['price_thb']:,} บาท\n"
                f"รายละเอียด: {product['specifications']}"
            )

        return (
            "พบข้อมูลสินค้าจากฐานข้อมูล VITALFORM Demo ดังนี้:\n\n"
            + "\n\n".join(lines)
            + "\n\n"
            + disclaimer
        )

    @staticmethod
    def _build_mock_field_value(
        field_name: str,
        annotation: Any,
        context: dict
    ) -> Any:
        """Build a schema-compatible value without calling an external LLM."""
        name = field_name.lower()
        products = context["products"]
        answer = context["answer"]

        # Map common response field names.
        if name in {
            "answer", "response", "reply", "message",
            "content", "text", "output", "summary"
        }:
            return answer

        if name in {"provider", "model_provider", "source_provider"}:
            return "mock"

        if name in {"is_mock", "mock_mode", "fallback_used"}:
            return True

        if name in {"products", "items", "results", "matched_products"}:
            return products

        if name in {"product", "matched_product"}:
            return products[0] if products else None

        if name in {"sku", "product_sku"}:
            return products[0]["sku"] if products else ""

        if name in {"confidence", "score"}:
            return 0.0 if not products else 0.85

        if name in {"sources", "citations", "references"}:
            return []

        # Support Optional, Union and Literal annotations.
        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is Union:
            non_none = [arg for arg in args if arg is not type(None)]
            if not non_none:
                return None
            return AIFactory._build_mock_field_value(
                field_name, non_none[0], context
            )

        if origin is Literal:
            return args[0] if args else None

        # Support lists and dictionaries.
        if origin is list:
            item_type = args[0] if args else Any
            if name in {"products", "items", "results", "matched_products"}:
                return products
            return []

        if origin is dict:
            return {}
        
        # Support nested Pydantic models.
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested_data = {}

            for nested_name, nested_field in annotation.model_fields.items():
                nested_data[nested_name] = (
                    AIFactory._build_mock_field_value(
                        nested_name,
                        nested_field.annotation,
                        context
                    )
                )

            return annotation.model_validate(nested_data)

        # Primitive types.
        if annotation is str:
            return answer
        if annotation is bool:
            return False
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is Any:
            return answer

        # Last-resort value for unknown annotations.
        return None

    @staticmethod
    def _call_mock_structured(
        prompt: str,
        response_schema: type[BaseModel]
    ) -> Any:
        """Local VITALFORM fallback. No API key or network required."""
        products = AIFactory._find_vitalform_products(prompt)
        answer = AIFactory._build_mock_answer(prompt, products)

        context = {
            "products": products,
            "answer": answer,
        }

        mock_data = {}

        for field_name, field_info in response_schema.model_fields.items():
            if not field_info.is_required():
                continue

            mock_data[field_name] = AIFactory._build_mock_field_value(
                field_name,
                field_info.annotation,
                context
            )

        logger.warning(
            "Using local Mock Provider. Matched %s VITALFORM product(s).",
            len(products)
        )

        return response_schema.model_validate(mock_data)

   
    @staticmethod
    def _call_gemini_with_retry(
        client: genai.Client,
        prompt: str,
        response_schema: type[BaseModel],
        model_name: str = "gemini-3.8-flash",
        max_retries: int = 4
    ) -> Any:
        """
        Calls Gemini with retry handling.

        - Temporary errors: retry with exponential backoff.
        - Daily quota exhausted: immediately raise to trigger Mock fallback.
        - Other errors: immediately raise to the caller.
        """

        last_exception = None

        transient_error_codes = (
            "500",
            "502",
            "503",
            "504",
            "INTERNAL",
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "429",
        )

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
                error_msg = str(e)
                error_lower = error_msg.lower()

                # 1. Detect daily quota exhaustion.
                # Retrying cannot fix a daily request limit.
                is_daily_quota = any(
                    indicator in error_lower
                    for indicator in (
                        "per day",
                        "requestsperday",
                        "generate_content_free_tier_requests",
                        "per_day",
                    )
                )

                if is_daily_quota:
                    logger.error(
                        "Gemini daily quota exhausted for %s. "
                        "Skipping retries and triggering fallback. Error: %s",
                        model_name,
                        error_msg,
                    )
                    raise

                # 2. Detect temporary errors.
                is_transient = any(
                    code in error_msg
                    for code in transient_error_codes
                )

                # 3. Retry temporary errors if attempts remain.
                if is_transient and attempt < max_retries - 1:
                    wait_time = (
                        (2 ** attempt) + random.uniform(0.1, 0.5)
                    )

                    logger.warning(
                        "Gemini (%s) transient error "
                        "(attempt %s/%s). Retrying in %.2fs. Error: %s",
                        model_name,
                        attempt + 1,
                        max_retries,
                        wait_time,
                        error_msg,
                    )

                    time.sleep(wait_time)
                    continue

                # 4. Stop retrying and let generate_structured_json()
                # handle the error and activate the fallback.
                logger.error(
                    "Gemini (%s) failed after attempt %s/%s. "
                    "Passing error to fallback handler. Error: %s",
                    model_name,
                    attempt + 1,
                    max_retries,
                    error_msg,
                )
                raise

        # Defensive fallback; normally the loop either returns or raises.
        if last_exception:
            raise last_exception

        raise RuntimeError("Gemini request failed without an exception.")



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
    def generate_structured_json(
        prompt: str,
        response_schema: type[BaseModel],
        provider: Optional[str] = None
    ) -> Any:
        """
        Routes structured generation to the selected provider.
        Gemini overload falls back to another configured provider,
        then to the local Mock Provider.
        """
        target_provider = provider or settings.DEFAULT_LLM_PROVIDER

        # Explicit local Mock mode
        if target_provider == "mock":
            return AIFactory._call_mock_structured(prompt, response_schema)

        if target_provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise HTTPException(
                    status_code=500,
                    detail="OpenAI API key missing."
                )

            try:
                return AIFactory._call_openai_structured(
                    prompt, response_schema
                )
            except Exception as e:
                logger.exception("OpenAI generation failed.")
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenAI SDK Error: {str(e)}"
                )

        elif target_provider == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.warning(
                    "Gemini API key missing. Falling back to local Mock Provider."
                )
                return AIFactory._call_mock_structured(
                    prompt, response_schema
                )

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

                overload_codes = (
                    "500", "502", "503", "504",
                    "INTERNAL", "UNAVAILABLE",
                    "RESOURCE_EXHAUSTED", "429"
                )

                is_overload = any(
                    code in error_str for code in overload_codes
                )

                if not is_overload:
                    logger.exception(
                        "Gemini failed with a non-overload error."
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=f"Gemini SDK Error: {error_str}"
                    )

                logger.warning(
                    "Gemini overloaded after retries. Starting fallback chain."
                )

                # Optional OpenAI fallback
                if settings.OPENAI_API_KEY:
                    try:
                        logger.info("Trying OpenAI fallback.")
                        return AIFactory._call_openai_structured(
                            prompt, response_schema
                        )
                    except Exception as openai_err:
                        logger.error(
                            "OpenAI fallback failed: %s", openai_err
                        )

                # Optional Anthropic fallback
                if settings.ANTHROPIC_API_KEY:
                    try:
                        logger.info("Trying Anthropic fallback.")
                        return AIFactory._call_anthropic_structured(
                            prompt, response_schema
                        )
                    except Exception as anthropic_err:
                        logger.error(
                            "Anthropic fallback failed: %s", anthropic_err
                        )

                # Final fallback: Local Mock Provider
                logger.warning(
                    "Cloud providers unavailable. Using local Mock Provider."
                )

                return AIFactory._call_mock_structured(
                    prompt, response_schema
                )

        elif target_provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise HTTPException(
                    status_code=500,
                    detail="Anthropic API key missing."
                )

            try:
                return AIFactory._call_anthropic_structured(
                    prompt, response_schema
                )
            except Exception as e:
                logger.exception("Anthropic generation failed.")
                raise HTTPException(
                    status_code=502,
                    detail=f"Anthropic SDK Error: {str(e)}"
                )

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
