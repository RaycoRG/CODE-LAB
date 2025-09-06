from typing import Dict, Any
from .base_scraper import BaseScraper
from .hacienda_scraper import HaciendaCanariasScraper
from .gobcan_scraper import GobcanScraper
from .cabildo_scraper import CabildoScraper
from .ayuntamiento_scraper import AyuntamientoScraper
from .seguridad_social_scraper import SeguridadSocialScraper


class ScraperFactory:
    """Factory para crear instancias de scrapers específicos"""
    
    SCRAPER_CLASSES = {
        'HaciendaCanariasScraper': HaciendaCanariasScraper,
        'GobcanScraper': GobcanScraper,
        'CabildoScraper': CabildoScraper,
        'AyuntamientoScraper': AyuntamientoScraper,
        'SeguridadSocialScraper': SeguridadSocialScraper,
    }
    
    @classmethod
    def create_scraper(cls, institution: str, config: Dict[str, Any], scraping_config) -> BaseScraper:
        """Crea una instancia de scraper para la institución especificada"""
        
        scraper_class_name = config.get('scraper_class')
        if not scraper_class_name or scraper_class_name not in cls.SCRAPER_CLASSES:
            raise ValueError(f"Scraper no encontrado para {institution}: {scraper_class_name}")
        
        scraper_class = cls.SCRAPER_CLASSES[scraper_class_name]
        
        return scraper_class(
            base_url=config['base_url'],
            config=config,
            scraping_config=scraping_config
        )