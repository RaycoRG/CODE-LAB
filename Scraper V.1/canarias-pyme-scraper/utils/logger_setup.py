import logging
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

# Inicializar colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Formatter personalizado con colores"""
    
    COLOR_MAP = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA
    }
    
    def format(self, record):
        color = self.COLOR_MAP.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_logging(level="INFO"):
    """Configura el sistema de logging"""
    
    # Crear directorio de logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logger principal
    logger = logging.getLogger("canarias_scraper")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Limpiar handlers existentes
    logger.handlers.clear()
    
    # Handler para consola con colores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo
    log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger