# institution_scrapers/__init__.py - Archivo de inicialización del paquete
"""
Scrapers especializados para instituciones canarias
"""

from .base_scraper import BaseScraper
from .hacienda_scraper import HaciendaCanariasScraper
from .gobcan_scraper import GobcanScraper
from .cabildo_scraper import CabildoScraper
from .ayuntamiento_scraper import AyuntamientoScraper
from .seguridad_social_scraper import SeguridadSocialScraper
from .scraper_factory import ScraperFactory

__all__ = [
    'BaseScraper',
    'HaciendaCanariasScraper', 
    'GobcanScraper',
    'CabildoScraper',
    'AyuntamientoScraper',
    'SeguridadSocialScraper',
    'ScraperFactory'
]