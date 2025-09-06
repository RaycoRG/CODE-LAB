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
            
            # Realizar petición
            if method.upper() == 'GET':
                response = self.session.get(url, **request_params)
            elif method.upper() == 'POST':
                response = self.session.post(url, **request_params)
            else:
                response = self.session.request(method, url, **request_params)
            
            # Verificar código de estado
            response.raise_for_status()
            
            # Log de respuesta exitosa
            self.logger.debug(f"Petición exitosa: {url} - Status: {response.status_code}")
            
            # Respetar rate limiting
            time.sleep(self.scraping_config.REQUEST_DELAY)
            
            return response
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout en petición: {url}")
            raise
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Error de conexión: {url}")
            raise
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"Error HTTP {e.response.status_code}: {url}")
            if e.response.status_code == 429:  # Too Many Requests
                time.sleep(self.scraping_config.RATE_LIMIT_DELAY)
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado en petición {url}: {str(e)}")
            raise
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Parsea contenido HTML con BeautifulSoup"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
        except Exception as e:
            self.logger.error(f"Error parseando HTML: {str(e)}")
            raise
    
    def _extract_document_info(self, link, base_url: str) -> Optional[Dict]:
        """Extrae información de un enlace a documento"""
        try:
            href = link.get('href', '')
            if not href:
                return None
            
            # Resolver URL completa
            full_url = self._resolve_url(href, base_url)
            
            # Verificar si es un documento válido
            if not self._is_valid_document_url(full_url):
                return None
            
            # Extraer información del enlace
            title = link.get_text(strip=True)
            if not title:
                title = link.get('title', '')
            
            # Información adicional
            doc_info = {
                'url': full_url,
                'title': title,
                'source_url': base_url,
                'institution': self.__class__.__name__.replace('Scraper', ''),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Intentar extraer tipo de documento de la URL
            doc_type = self._extract_document_type(full_url)
            if doc_type:
                doc_info['document_type'] = doc_type
            
            return doc_info
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo info de documento: {str(e)}")
            return None
    
    def _is_valid_document_url(self, url: str) -> bool:
        """Verifica si una URL corresponde a un documento válido"""
        try:
            # Extensiones de documentos válidos
            valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
            
            url_lower = url.lower()
            
            # Verificar extensión
            if any(url_lower.endswith(ext) for ext in valid_extensions):
                return True
            
            # Verificar patrones en la URL
            doc_patterns = ['documento', 'formulario', 'modelo', 'impreso', 'download']
            if any(pattern in url_lower for pattern in doc_patterns):
                return True
            
            return False
            
        except Exception:
            return False
    
    def _extract_document_type(self, url: str) -> Optional[str]:
        """Extrae el tipo de documento de la URL"""
        try:
            url_lower = url.lower()
            
            if '.pdf' in url_lower:
                return 'PDF'
            elif any(ext in url_lower for ext in ['.doc', '.docx']):
                return 'Word'
            elif any(ext in url_lower for ext in ['.xls', '.xlsx']):
                return 'Excel'
            elif any(ext in url_lower for ext in ['.ppt', '.pptx']):
                return 'PowerPoint'
            
            return None
            
        except Exception:
            return None
    
    def _resolve_url(self, href: str, base_url: str) -> str:
        """Resuelve URL relativa a absoluta"""
        try:
            return urljoin(base_url, href)
        except Exception as e:
            self.logger.debug(f"Error resolviendo URL {href}: {str(e)}")
            return href
    
    def _filter_documents_by_type(self, documents: List[Dict], doc_types: Optional[List[str]]) -> List[Dict]:
        """Filtra documentos por tipo si se especifica"""
        if not doc_types:
            return documents
        
        filtered = []
        for doc in documents:
            doc_type = doc.get('document_type', '').lower()
            if any(dt.lower() in doc_type for dt in doc_types):
                filtered.append(doc)
        
        return filtered
    
    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """Elimina documentos duplicados basándose en URL"""
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_docs.append(doc)
        
        return unique_docs
    
    def validate_config(self) -> bool:
        """Valida la configuración del scraper"""
        try:
            # Verificar URL base
            if not self.base_url:
                self.logger.error("URL base no especificada")
                return False
            
            # Verificar que la URL es válida
            parsed = urlparse(self.base_url)
            if not parsed.scheme or not parsed.netloc:
                self.logger.error(f"URL base inválida: {self.base_url}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando configuración: {str(e)}")
            return False
    
    @abstractmethod
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Método abstracto que debe implementar cada scraper específico"""
        pass
    
    def __enter__(self):
        """Contexto manager - entrada"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Contexto manager - salida"""
        try:
            self.session.close()
        except Exception:
            pass