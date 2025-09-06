"""
Configuración centralizada para el sistema de scraping PYME Canarias
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ScrapingConfig:
    """Configuración centralizada del sistema de scraping"""
    
    # Configuración por defecto
    DEFAULT_CONFIG = {
        "OUTPUT_DIR": "./documents",
        "LOG_LEVEL": "INFO",
        "MAX_RETRIES": 3,
        "REQUEST_TIMEOUT": 30,
        "DELAY_BETWEEN_REQUESTS": 2,
        "MAX_DOCUMENTS_PER_INSTITUTION": 50,
        "ENABLE_DEDUPLICATION": True,
        "RESPECT_ROBOTS_TXT": True
    }
    
    # Headers HTTP por defecto
    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # Fuentes de datos objetivo
    TARGET_SOURCES = {
        "hacienda_canarias": {
            "base_url": "https://www.gobiernodecanarias.org/hacienda/",
            "areas": ["tributaria", "empresas", "autonomos", "impuestos"],
            "scraper_class": "HaciendaCanariasScraper",
            "priority": 1
        },
        "gobcan": {
            "base_url": "https://www.gobiernodecanarias.org/",
            "areas": ["economia", "empleo", "industria", "turismo"],
            "scraper_class": "GobcanScraper",
            "priority": 2
        },
        "cabildo_tenerife": {
            "base_url": "https://www.tenerife.es/",
            "areas": ["empresas", "empleo", "economia", "desarrollo"],
            "scraper_class": "CabildoScraper",
            "priority": 3
        },
        "cabildo_grancanaria": {
            "base_url": "https://www.grancanaria.com/",
            "areas": ["empresas", "desarrollo", "economia"],
            "scraper_class": "CabildoScraper",
            "priority": 3
        },
        "ayto_santacruz": {
            "base_url": "https://www.santacruzdetenerife.es/",
            "areas": ["licencias", "empresas", "tramites"],
            "scraper_class": "AyuntamientoScraper",
            "priority": 4
        },
        "ayto_laspalmas": {
            "base_url": "https://www.laspalmasgc.es/",
            "areas": ["licencias", "empresas", "tramites"],
            "scraper_class": "AyuntamientoScraper",
            "priority": 4
        },
        "seguridad_social": {
            "base_url": "https://www.seg-social.es/",
            "areas": ["autonomos", "empresas", "cotizacion", "afiliacion"],
            "scraper_class": "SeguridadSocialScraper",
            "priority": 2
        },
        "sepe_canarias": {
            "base_url": "https://www.sepe.es/HomeSepe/Personas/distributiva-prestaciones/donde-y-como-solicitar-prestacion",
            "areas": ["prestaciones", "empresas", "trabajadores"],
            "scraper_class": "SepeScraper",
            "priority": 3
        },
        "camara_comercio_tenerife": {
            "base_url": "https://www.camaratenerife.com/",
            "areas": ["empresas", "emprendimiento", "formacion", "comercio"],
            "scraper_class": "CamaraComercioScraper",
            "priority": 3
        },
        "camara_comercio_grancanaria": {
            "base_url": "https://www.camaralaspalmas.es/",
            "areas": ["empresas", "emprendimiento", "comercio"],
            "scraper_class": "CamaraComercioScraper",
            "priority": 3
        }
    }
    
    # Tipos de documentos válidos
    VALID_DOCUMENT_TYPES = [
        "Formulario", "Modelo", "Guía", "Manual", "Instructivo",
        "Ley", "Decreto", "Orden", "Resolución", "Reglamento",
        "Normativa", "Bases", "Convocatoria", "Solicitud"
    ]
    
    # Extensiones de archivos válidas
    VALID_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']
    
    def __init__(self, config_path: Optional[str] = None):
        """Inicializa la configuración"""
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Cargar configuración personalizada si existe
        if config_path and os.path.exists(config_path):
            self._load_custom_config(config_path)
        
        # Aplicar variables de entorno
        self._apply_env_vars()
        
        # Crear propiedades para acceso directo
        self._create_properties()
    
    def _load_custom_config(self, config_path: str):
        """Carga configuración personalizada desde archivo JSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                self.config.update(custom_config)
        except Exception as e:
            logging.warning(f"Error cargando configuración personalizada: {e}")
    
    def _apply_env_vars(self):
        """Aplica variables de entorno"""
        env_mappings = {
            'SCRAPER_OUTPUT_DIR': 'OUTPUT_DIR',
            'SCRAPER_LOG_LEVEL': 'LOG_LEVEL',
            'SCRAPER_MAX_RETRIES': 'MAX_RETRIES',
            'SCRAPER_REQUEST_TIMEOUT': 'REQUEST_TIMEOUT',
            'SCRAPER_DELAY': 'DELAY_BETWEEN_REQUESTS'
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value:
                # Convertir tipos apropiadamente
                if config_key in ['MAX_RETRIES', 'REQUEST_TIMEOUT']:
                    self.config[config_key] = int(env_value)
                elif config_key == 'DELAY_BETWEEN_REQUESTS':
                    self.config[config_key] = float(env_value)
                else:
                    self.config[config_key] = env_value
    
    def _create_properties(self):
        """Crea propiedades para acceso directo a la configuración"""
        for key, value in self.config.items():
            setattr(self, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Establece un valor de configuración"""
        self.config[key] = value
        setattr(self, key, value)
    
    def create_directories(self):
        """Crea los directorios necesarios"""
        base_dir = Path(self.OUTPUT_DIR)
        
        # Crear directorios por categoría
        categories = ["fiscal", "laboral", "municipal", "autonomico", "general"]
        for category in categories:
            (base_dir / category).mkdir(parents=True, exist_ok=True)
        
        # Crear directorio de logs
        Path("logs").mkdir(exist_ok=True)
    
    def save_config(self, path: str):
        """Guarda la configuración actual a un archivo"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
    
    def validate_config(self) -> bool:
        """Valida la configuración actual"""
        required_keys = ['OUTPUT_DIR', 'LOG_LEVEL', 'MAX_RETRIES', 'REQUEST_TIMEOUT']
        
        for key in required_keys:
            if key not in self.config:
                logging.error(f"Falta configuración requerida: {key}")
                return False
        
        # Validar tipos
        if not isinstance(self.config['MAX_RETRIES'], int) or self.config['MAX_RETRIES'] < 1:
            logging.error("MAX_RETRIES debe ser un entero mayor a 0")
            return False
        
        if not isinstance(self.config['REQUEST_TIMEOUT'], (int, float)) or self.config['REQUEST_TIMEOUT'] < 1:
            logging.error("REQUEST_TIMEOUT debe ser un número mayor a 0")
            return False
        
        return True