import sys
import time
import logging
import uuid
from typing import Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure unified standard logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Request-ID: %(request_id)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("nexus_telemetry")

class TelemetryMiddleware(BaseHTTPMiddleware):
    """Intercepts active requests to log trace IDs and track processing times."""
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()
        
        # Attach the Request ID across the operational log context
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record
        logging.setLogRecordFactory(record_factory)

        logger.info(f"Incoming Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        duration = time.perf_counter() - start_time
        logger.info(f"Completed Request: Status {response.status_code} in {duration:.4f}s")
        
        response.headers["X-Request-ID"] = request_id
        return response

def track_token_cost(prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
    """Calculates live cost metrics to help monitor external API spending."""
    rates: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
        "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000}
    }
    
    selected = rates.get(model_name, {"input": 0.0, "output": 0.0})
    total_cost = (prompt_tokens * selected["input"]) + (completion_tokens * selected["output"])
    
    logger.info(f"AI Analytics Token Track -> Model: {model_name} | Cost: ${total_cost:.6f}")
    return total_cost
