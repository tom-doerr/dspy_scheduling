import time
import json
from functools import wraps
from models import SessionLocal, DSPyExecution
import logging

logger = logging.getLogger(__name__)

def track_dspy_execution(module_name: str, **input_params):
    """Track DSPy module execution with inputs and outputs"""
    start_time = time.time()

    # Log start
    logger.info(f"🚀 DSPy Inference STARTED - Module: {module_name}")
    logger.info(f"📥 INPUT - {json.dumps(input_params, default=str)}")

    def execute(func):
        # Execute the function
        result = func()

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log output
        logger.info(f"📤 OUTPUT - {str(result)}")
        logger.info(f"⏱️  Duration: {duration_ms:.2f}ms")
        logger.info(f"✅ DSPy Inference COMPLETED - Module: {module_name}")

        # Store in database
        db = SessionLocal()
        try:
            execution = DSPyExecution(
                module_name=module_name,
                inputs=json.dumps(input_params, default=str),
                outputs=str(result),
                duration_ms=duration_ms
            )
            db.add(execution)
            db.commit()
        finally:
            db.close()

        return result

    return execute
