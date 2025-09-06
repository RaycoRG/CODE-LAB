"""
Factory para crear instancias de scrapers específicos
Versión actualizada con todos los scrapers
"""

from typing import Dict, Any
from .base_scraper import BaseScraper
from .hacienda_scraper import HaciendaCanariasScraper
from .gobcan_scraper import GobcanScraper
from .cabildo_scraper import CabildoScraper
from .ayuntamiento_scraper import AyuntamientoScraper
from .seguridad_social_scraper import SeguridadSocialScraper


class ScraperFactory:
    """Factory para crear instancias de scrapers específicos"""
    
    # Mapeo de nombres de clase a clases reales
    SCRAPER_CLASSES = {
        'HaciendaCanariasScraper': HaciendaCanariasScraper,
        'GobcanScraper': GobcanScraper,
        'CabildoScraper': CabildoScraper,
        'AyuntamientoScraper': AyuntamientoScraper,
        'SeguridadSocialScraper': SeguridadSocialScraper,
    }
    
    @classmethod
    def register_scraper(cls, name: str, scraper_class):
        """Registra un nuevo scraper dinámicamente"""
        if not issubclass(scraper_class, BaseScraper):
            raise ValueError(f"La clase {scraper_class.__name__} debe heredar de BaseScraper")
        
        cls.SCRAPER_CLASSES[name] = scraper_class
    
    @classmethod
    def create_scraper(cls, institution: str, config: Dict[str, Any], scraping_config) -> BaseScraper:
        """Crea una instancia de scraper para la institución especificada"""
        
        scraper_class_name = config.get('scraper_class')
        if not scraper_class_name:
            raise ValueError(f"No se especificó scraper_class para {institution}")
        
        # Intentar importar scrapers adicionales si no están registrados
        if scraper_class_name not in cls.SCRAPER_CLASSES:
            cls._try_import_additional_scrapers()
        
        if scraper_class_name not in cls.SCRAPER_CLASSES:
            raise ValueError(f"Scraper no encontrado para {institution}: {scraper_class_name}")
        
        scraper_class = cls.SCRAPER_CLASSES[scraper_class_name]
        
        # Validar configuración mínima
        if 'base_url' not in config:
            raise ValueError(f"Falta base_url en configuración para {institution}")
        
        try:
            return scraper_class(
                base_url=config['base_url'],
                config=config,
                scraping_config=scraping_config
            )
        except Exception as e:
            raise RuntimeError(f"Error creando scraper para {institution}: {str(e)}")
    
    @classmethod
    def _try_import_additional_scrapers(cls):
        """Intenta importar scrapers adicionales dinámicamente"""
        additional_scrapers = [
            ('SepeScraper', 'sepe_scraper', 'SepeScraper'),
            ('CamaraComercioScraper', 'camara_comercio_scraper', 'CamaraComercioScraper'),
        ]
        
        for class_name, module_name, import_name in additional_scrapers:
            if class_name not in cls.SCRAPER_CLASSES:
                try:
                    module = __import__(f'institution_scrapers.{module_name}', 
                                      fromlist=[import_name])
                    scraper_class = getattr(module, import_name)
                    cls.SCRAPER_CLASSES[class_name] = scraper_class
                except ImportError:
                    pass  # Scraper adicional no disponible
                except Exception as e:
                    import logging
                    logger = logging.getLogger("canarias_scraper.factory")
                    logger.debug(f"Error importando {class_name}: {e}")
    
    @classmethod
    def get_available_scrapers(cls) -> Dict[str, str]:
        """Retorna un diccionario de scrapers disponibles"""
        cls._try_import_additional_scrapers()
        
        return {name: scraper_class.__doc__ or "Sin descripción" 
                for name, scraper_class in cls.SCRAPER_CLASSES.items()}
    
    @classmethod
    def validate_scraper_config(cls, institution: str, config: Dict[str, Any]) -> bool:
        """Valida la configuración de un scraper específico"""
        try:
            # Verificar campos requeridos
            required_fields = ['base_url', 'scraper_class']
            for field in required_fields:
                if field not in config:
                    return False
            
            # Verificar que la clase existe
            scraper_class_name = config['scraper_class']
            cls._try_import_additional_scrapers()
            
            if scraper_class_name not in cls.SCRAPER_CLASSES:
                return False
            
            # Verificar URL válida
            from urllib.parse import urlparse
            parsed_url = urlparse(config['base_url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
            
            return True
            
        except Exception:
            return False