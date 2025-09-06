import time
import logging
import requests
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from utils.retry_decorator import with_retry


class BaseScraper(ABC):
    """Clase base para todos los scrapers de instituciones"""
    
    def __init__(self, base_url: str, config: dict, scraping_config):
        self.base_url = base_url
        self.config = config
        self.scraping_config = scraping_config
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = logging.getLogger(f"canarias_scraper.{self.__class__.__name__}")
        
        # Configurar sesión
        self._setup_session()
    
    def _setup_session(self):
        """Configura la sesión HTTP"""
        self.session.headers.update(self.scraping_config.DEFAULT_HEADERS)
        self.session.headers['User-Agent'] = self.ua.random
    
    @with_retry(max_retries=3, delay=1)
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Realiza una petición HTTP con manejo de errores"""
        try:
            self.logger.debug(f"Request: {url}")
            
            # Rotar User-Agent ocasionalmente
            if hash(url) % 10 == 0:  # 10% de las veces
                self.session.headers['User-Agent'] = self.ua.random
            
            response = self.session.get(
                url, 
                timeout=self.scraping_config.REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            
            # Delay entre requests
            time.sleep(self.scraping_config.DELAY_BETWEEN_REQUESTS)
            
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Error en request {url}: {str(e)}")
            raise
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Parsea contenido HTML"""
        return BeautifulSoup(html_content, 'lxml')
    
    def _is_valid_document_url(self, url: str) -> bool:
        """Verifica si una URL apunta a un documento válido"""
        valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        return any(path.endswith(ext) for ext in valid_extensions)
    
    def _extract_document_info(self, link_element, base_url: str) -> Optional[Dict]:
        """Extrae información básica de un elemento de enlace a documento"""
        try:
            # Obtener URL
            href = link_element.get('href')
            if not href:
                return None
            
            document_url = urljoin(base_url, href)
            
            # Verificar si es un documento válido
            if not self._is_valid_document_url(document_url):
                return None
            
            # Obtener título
            title = (link_element.get_text(strip=True) or 
                    link_element.get('title', '') or 
                    link_element.get('alt', ''))
            
            if not title:
                # Intentar obtener título del nombre del archivo
                filename = urlparse(document_url).path.split('/')[-1]
                title = filename.replace('%20', ' ').replace('_', ' ')
            
            return {
                'title': title,
                'download_url': document_url,
                'type': self._detect_document_type(title),
                'source_url': base_url
            }
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo info de documento: {e}")
            return None
    
    def _detect_document_type(self, title: str) -> str:
        """Detecta el tipo de documento basado en el título"""
        title_lower = title.lower()
        
        type_keywords = {
            'Formulario': ['modelo', 'formulario', 'impreso'],
            'Guía': ['guia', 'manual', 'instrucciones'],
            'Ley': ['ley', 'decreto', 'orden', 'resolucion'],
            'Reglamento': ['reglamento', 'normativa', 'bases']
        }
        
        for doc_type, keywords in type_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return doc_type
        
        return 'Documento'
    
    @abstractmethod
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Método abstracto para scrapear documentos de la institución"""
        pass
    
    @abstractmethod
    def _get_document_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Método abstracto para extraer enlaces a documentos"""
        pass