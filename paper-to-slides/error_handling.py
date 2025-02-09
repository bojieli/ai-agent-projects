import functools
import time
import logging

logger = logging.getLogger(__name__)

def retry(max_retries=3, delay=1, backoff=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Attempt {retries+1} failed: {str(e)}")
                    if retries == max_retries - 1:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
                    retries += 1
        return wrapper
    return decorator

def validate_input(*required_fields):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for field in required_fields:
                if not kwargs.get(field):
                    raise ValueError(f"Missing required field: {field}")
            return func(*args, **kwargs)
        return wrapper
    return decorator 