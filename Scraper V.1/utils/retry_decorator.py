import time
import logging
from functools import wraps
from typing import Callable


def with_retry(max_retries: int = 3, delay: float = 1, backoff: float = 2):
    """Decorador para reintentos con exponential backoff"""
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("canarias_scraper.retry")
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"❌ Falló después de {max_retries} intentos: {str(e)}")
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"Intento {attempt + 1} falló, reintentando en {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator