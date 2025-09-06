"""
Clase base para todos los scrapers de instituciones

"""

import time
import logging
import requests
import urllib.robotparser
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse, quote
from utils.retry_decorator import with_retry


class BaseScraper(ABC):
    """Clase base para todos los scrapers de instituciones"""
    
    def __init__(self, base_url: str, config: Dict, scraping_config):
        """Inicializa el scraper base"""
        self.base_url = base_url.rstrip('/')  # Normalizar URL base
        self.config = config
        self.scraping_config = scraping_config
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = logging.getLogger(f"canarias_scraper.{self.__class__.__name__}")
        
        # Cache para robots.txt
        self.robots_cache = {}
        
        # Configurar sesión
        self._setup_session()
        
        # Verificar robots.txt si está habilitado
        if self.scraping_config.get('RESPECT_ROBOTS_TXT', True):
            self._check_robots_txt()
    
    def _setup_session(self):
        """Configura la sesión HTTP con headers apropiados"""
        try:
            # Headers base
            self.session.headers.update(self.scraping_config.DEFAULT_HEADERS)
            
            # User-Agent inicial
            self.session.headers['User-Agent'] = self.ua.random
            
            # Configurar adaptadores con pool de conexiones
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=10,
                max_retries=0  # Manejamos reintentos manualmente
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
            
            self.logger.debug("Sesión HTTP configurada correctamente")
            
        except Exception as e:
            self.logger.warning(f"Error configurando sesión: {e}")
    
    def _check_robots_txt(self):
        """Verifica y respeta robots.txt"""
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            
            if robots_url in self.robots_cache:
                return
            
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            self.robots_cache[robots_url] = rp
            self.logger.debug(f"robots.txt cargado desde: {robots_url}")
            
        except Exception as e:
            self.logger.debug(f"No se pudo cargar robots.txt: {e}")
            self.robots_cache[urljoin(self.base_url, '/robots.txt')] = None
    
    def _can_fetch(self, url: str) -> bool:
        """Verifica si se puede hacer scraping de una URL según robots.txt"""
        if not self.scraping_config.get('RESPECT_ROBOTS_TXT', True):
            return True
        
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            rp = self.robots_cache.get(robots_url)
            
            if rp is None:
                return True  # Si no hay robots.txt, permitir
            
            user_agent = self.session.headers.get('User-Agent', '*')
            return rp.can_fetch(user_agent, url)
            
        except Exception:
            return True  # En caso de error, permitir
    
    @with_retry(max_retries=3, delay=1, backoff=2)
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Realiza una petición HTTP con manejo completo de errores"""
        try:
            # Verificar robots.txt
            if not self._can_fetch(url):
                self.logger.warning(f"Bloqueado por robots.txt: {url}")
                return None
            
            # Log de la petición
            self.logger.debug(f"Realizando petición {method}: {url}")
            
            # Rotar User-Agent ocasionalmente
            if hash(url) % 15 == 0:  # ~6.7% de las veces
                self.session.headers['User-Agent'] = self.ua.random
                self.logger.debug("User-Agent rotado")
            
            # Preparar parámetros de la petición
            request_params = {
                'timeout': self.scraping_config.REQUEST_TIMEOUT,
                'allow_redirects': True,
                **kwargs
            }
            
            # Realizar