import time
import json
from functools import wraps
from models import SessionLocal, DSPyExecution
import logging

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

def track_dspy_execution(module_name: str, **input_params):
    """Track DSPy module execution with inputs and outputs"""
    start_time = time.time()

    # Log start
    logger.info(f"🚀 DSPy Inference STARTED - Module: {module_name}")
    logger.info(f"📥 INPUT - {_safe_serialize(input_params, use_json=True)}")

    def execute(func):
        # Execute the function
        result = func()

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log output
        logger.info(f"📤 OUTPUT - {_safe_serialize(result, use_json=False)}")
        logger.info(f"⏱️  Duration: {duration_ms:.2f}ms")
        logger.info(f"✅ DSPy Inference COMPLETED - Module: {module_name}")

        # Store in database
        db = SessionLocal()
        try:
            execution = DSPyExecution(
                module_name=module_name,
                inputs=_safe_serialize(input_params, use_json=True),
                outputs=_safe_serialize(result, use_json=False),
                duration_ms=duration_ms
            )
            db.add(execution)
            db.commit()
        finally:
            db.close()

        return result

    return execute
