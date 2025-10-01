import time
import json
from functools import wraps
from models import SessionLocal, DSPyExecution
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError, DBAPIError

logger = logging.getLogger(__name__)

def _safe_serialize(obj, use_json=True):
    """Safely serialize an object with fallback to repr()"""
    try:
        if use_json:
            return json.dumps(obj, default=str)
        else:
            return str(obj)
    except Exception as e:
        logger.warning(f"Serialization failed, using repr(): {e}")
        try:
            return repr(obj)
        except Exception:
            return "<serialization failed>"

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((OperationalError, DBAPIError)),
    reraise=True
)
def _store_execution_with_retry(module_name: str, inputs: str, outputs: str, duration_ms: float):
    """Store DSPy execution in database with retry logic for transient failures"""
    db = SessionLocal()
    try:
        execution = DSPyExecution(
            module_name=module_name,
            inputs=inputs,
            outputs=outputs,
            duration_ms=duration_ms
        )
        db.add(execution)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def track_dspy_execution(module_name: str, **input_params):
    """Track DSPy module execution with inputs and outputs"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Log start
            logger.info(f"🚀 DSPy Inference STARTED - Module: {module_name}")
            logger.info(f"📥 INPUT - {_safe_serialize(input_params, use_json=True)}")

            # Execute the function
            result = func(*args, **kwargs)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log output
            logger.info(f"📤 OUTPUT - {_safe_serialize(result, use_json=False)}")
            logger.info(f"⏱️  Duration: {duration_ms:.2f}ms")
            logger.info(f"✅ DSPy Inference COMPLETED - Module: {module_name}")

            # Store in database with retry logic
            try:
                _store_execution_with_retry(
                    module_name=module_name,
                    inputs=_safe_serialize(input_params, use_json=True),
                    outputs=_safe_serialize(result, use_json=False),
                    duration_ms=duration_ms
                )
            except Exception as e:
                logger.error(f"Failed to store DSPy execution for {module_name} after retries: {e}")

            return result
        return wrapper
    return decorator
