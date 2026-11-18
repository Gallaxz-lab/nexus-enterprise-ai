
import hashlib
import logging
import re
from typing import Any, Optional, Union, Literal, get_args, get_origin

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AIFactory:
    """Local-only AI factory for stable VITALFORM demonstration mode."""

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
                "warranty_demo": "Frame 1 year; motor 1 year; parts 6 months",
            },
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
                "warranty_demo": "Frame 1 year; parts 6 months",
            },
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
                "warranty_demo": "6 months",
            },
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
                "safety_note": "Demo information only; not medical diagnosis",
            },
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
                "warranty_demo": "6 months",
            },
        },
    ]

    ALL_PRODUCT_KEYWORDS = (
        "สินค้าทั้งหมด",
        "รายการสินค้าทั้งหมด",
        "สินค้าทุกชนิด",
        "สินค้าทุกประเภท",
        "ดูสินค้าทั้งหมด",
        "มีสินค้าอะไรบ้าง",
        "มีสินค้าอะไร",
        "สินค้ามีอะไรบ้าง",
        "มีอะไรขายบ้าง",
        "ขอดูสินค้า",
        "ดูรายการสินค้า",
        "แสดงรายการสินค้า",
        "แสดงสินค้าทั้งหมด",
        "all products",
        "all items",
        "full catalog",
        "product catalog",
        "show me everything",
        "what products",
        "what items",
    )

    PRODUCT_ALIASES = {
        "VF-T100": ("ลู่วิ่ง", "treadmill", "runform", "t100"),
        "VF-R20": ("จักรยานออกกำลังกาย", "จักรยาน", "exercise bike", "spin", "r20"),
        "VF-D50": ("ดัมเบล", "dumbbell", "v-core", "d50"),
        "VF-BP01": ("เครื่องวัดความดัน", "เครื่องวัดความดันโลหิต", "blood pressure", "bp01"),
        "VF-S10": ("เครื่องชั่ง", "เครื่องชั่งน้ำหนัก", "digital scale", "balance", "s10"),
    }

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").lower()).strip()

    @staticmethod
    def _find_vitalform_products(prompt: str) -> list[dict]:
        """Find products requested by the customer."""

        query = AIFactory._normalize(prompt)

        if any(
            keyword in query
            for keyword in AIFactory.ALL_PRODUCT_KEYWORDS
        ):
            return AIFactory.VITALFORM_PRODUCTS

        matches = []

        for product in AIFactory.VITALFORM_PRODUCTS:
            sku = product["sku"]
            searchable_terms = [
                sku.lower(),
                product["name_th"].lower(),
                product["name_en"].lower(),
                *AIFactory.PRODUCT_ALIASES.get(sku, ()),
            ]

            if any(term in query for term in searchable_terms):
                matches.append(product)

        return matches

    @staticmethod
    def _format_specification(key: str, value: Any) -> str:
        labels = {
            "motor": "กำลังมอเตอร์",
            "speed_kmh": "ความเร็ว",
            "incline": "ระบบปรับความชัน",
            "running_surface_cm": "พื้นที่วิ่ง",
            "max_user_weight_kg": "รองรับน้ำหนักผู้ใช้สูงสุด",
            "foldable": "พับเก็บได้",
            "programs": "โปรแกรมออกกำลังกาย",
            "dimensions_cm": "ขนาดเครื่อง",
            "net_weight_kg": "น้ำหนักเครื่อง",
            "resistance": "ระบบแรงต้าน",
            "flywheel_kg": "น้ำหนักล้อช่วยแรง",
            "seat": "การปรับเบาะ",
            "weight_per_dumbbell_kg": "น้ำหนักต่อข้าง",
            "increment_kg": "ปรับน้ำหนักครั้งละ",
            "max_combined_weight_kg": "น้ำหนักรวมสูงสุด",
            "material": "วัสดุ",
            "measurement": "ระบบการวัด",
            "cuff_range_cm": "ช่วงขนาดผ้าพันแขน",
            "memory": "หน่วยความจำ",
            "display": "หน้าจอ",
            "power": "แหล่งพลังงาน",
            "capacity_kg": "รองรับน้ำหนักสูงสุด",
            "graduation_kg": "ความละเอียด",
            "warranty_demo": "การรับประกัน (ข้อมูลสาธิต)",
            "safety_note": "หมายเหตุ",
        }

        label = labels.get(key, key.replace("_", " ").capitalize())

        if isinstance(value, bool):
            value = "ได้" if value else "ไม่ได้"

        return f"{label}: {value}"

    @staticmethod
    def _build_mock_answer(
        prompt: str,
        products: list[dict],
    ) -> str:
        """Generate deterministic customer-facing answers."""

        query = AIFactory._normalize(prompt)

        disclaimer = (
            "\n\nหมายเหตุ: ข้อมูลสินค้า ราคา และคุณสมบัติทั้งหมดเป็นข้อมูลสมมติ "
            "สำหรับการสาธิตระบบ VITALFORM เท่านั้น"
        )

        if not products:
            return (
                "ขออภัยค่ะ ขณะนี้ยังไม่มีข้อมูลที่ตรงกับคำถามของคุณ "
                "กรุณาระบุชื่อสินค้าหรือรหัสสินค้าเพิ่มเติม "
                "หรือสอบถามเจ้าหน้าที่เพื่อยืนยันข้อมูลค่ะ"
                + disclaimer
            )

        asking_price = any(
            word in query
            for word in ("ราคา", "เท่าไหร่", "กี่บาท", "price", "cost")
        )

        asking_specs = any(
            word in query
            for word in (
                "คุณสมบัติ",
                "สเปก",
                "specification",
                "specifications",
                "spec",
                "รายละเอียด",
                "ขนาด",
                "น้ำหนัก",
                "ความเร็ว",
                "รับน้ำหนัก",
                "รับประกัน",
                "warranty",
                "feature",
                "features",
            )
        )

        if asking_price and len(products) == 1:
            product = products[0]
            return (
                f"{product['name_th']} ({product['name_en']}) "
                f"มีราคา {product['price_thb']:,} บาทค่ะ\n"
                f"รหัสสินค้า: {product['sku']}"
                + disclaimer
            )

        if asking_specs and len(products) == 1:
            product = products[0]
            specs = product["specifications"]

            details = "\n".join(
                AIFactory._format_specification(key, value)
                for key, value in specs.items()
            )

            return (
                f"รายละเอียดสินค้า {product['name_th']} "
                f"({product['name_en']})\n"
                f"รหัสสินค้า: {product['sku']}\n"
                f"ราคา: {product['price_thb']:,} บาท\n\n"
                f"คุณสมบัติ:\n{details}"
                + disclaimer
            )

        lines = []

        for product in products:
            lines.append(
                f"{product['name_th']} ({product['name_en']})\n"
                f"รหัสสินค้า: {product['sku']}\n"
                f"ราคา: {product['price_thb']:,} บาท"
            )

        heading = (
            "สินค้าทั้งหมดที่มีในระบบสาธิต:"
            if len(products) == len(AIFactory.VITALFORM_PRODUCTS)
            else "ข้อมูลสินค้าที่ตรงกับคำถามของคุณ:"
        )

        return heading + "\n\n" + "\n\n".join(lines) + disclaimer

    @staticmethod
    def _build_mock_field_value(
        field_name: str,
        annotation: Any,
        context: dict,
    ) -> Any:
        """Build values compatible with the requested Pydantic schema."""

        name = field_name.lower()
        products = context["products"]
        answer = context["answer"]

        if name in {
            "answer", "response", "reply", "message",
            "content", "text", "output", "summary",
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

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin in (Union, getattr(__import__("types"), "UnionType")):
            non_none = [
                arg for arg in args
                if arg is not type(None)
            ]
            if not non_none:
                return None

            return AIFactory._build_mock_field_value(
                field_name, non_none[0], context
            )

        if origin is Literal:
            return args[0] if args else None

        if origin is list:
            return products if name in {
                "products", "items", "results", "matched_products"
            } else []

        if origin is dict:
            return {}

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested_data = {}

            for nested_name, nested_field in annotation.model_fields.items():
                if nested_field.is_required():
                    nested_data[nested_name] = (
                        AIFactory._build_mock_field_value(
                            nested_name,
                            nested_field.annotation,
                            context,
                        )
                    )

            return annotation.model_validate(nested_data)

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

        return None

    @staticmethod
    def _call_mock_structured(
        prompt: str,
        response_schema: type[BaseModel],
        user_query: Optional[str] = None,
    ) -> Any:
        """Generate structured output locally without external AI services."""

        search_query = user_query if user_query else prompt

        products = AIFactory._find_vitalform_products(search_query)
        answer = AIFactory._build_mock_answer(search_query, products)

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
                context,
            )

        logger.info(
            "Mock Provider response generated. Query: %s | Products: %s",
            search_query,
            [product["sku"] for product in products],
        )

        return response_schema.model_validate(mock_data)

    @staticmethod
    def generate_structured_json(
        prompt: str,
        response_schema: type[BaseModel],
        provider: Optional[str] = None,
        user_query: Optional[str] = None,
    ) -> Any:
        """
        Mock-only structured generation.

        The provider argument is retained for compatibility with existing
        callers, but all requests are handled by the local Mock Provider.
        """

        logger.info(
            "Mock-only mode enabled. Ignoring configured provider: %s",
            provider or "default",
        )

        return AIFactory._call_mock_structured(
            prompt=prompt,
            response_schema=response_schema,
            user_query=user_query,
        )

    @staticmethod
    def generate_embedding(
        text_content: str,
        provider: Optional[str] = None,
    ) -> list[float]:
        """
        Generate a deterministic local 1536-dimensional vector.

        This is NOT a semantic embedding model. It is suitable only when
        document vectors and query vectors are generated using this same
        implementation.
        """

        normalized_text = (text_content or "").replace("\n", " ").strip()

        if not normalized_text:
            return [0.0] * 1536

        hash_bytes = hashlib.md5(
            normalized_text.encode("utf-8")
        ).digest()

        base_vector = []

        for i in range(1536):
            byte_idx = (i * 7) % len(hash_bytes)
            bit_idx = (i * 3) % 8

            bit_signal = (
                hash_bytes[byte_idx] >> bit_idx
            ) & 1

            char_weight = ord(
                normalized_text[i % len(normalized_text)]
            )

            value = (
                bit_signal * 0.5
                + (char_weight % 10) * 0.05
            )

            base_vector.append(value)

        magnitude = sum(
            value ** 2 for value in base_vector
        ) ** 0.5 or 1.0

        return [
            float(value / magnitude)
            for value in base_vector
        ]
