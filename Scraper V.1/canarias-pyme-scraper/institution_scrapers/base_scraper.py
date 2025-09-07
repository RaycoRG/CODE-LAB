# institution_scrapers/base_scraper.py - Versión mejorada
"""
Clase base mejorada para todos los scrapers de instituciones
"""

import time
import logging
import requests
import urllib.robotparser
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse, quote, unquote
from utils.retry_decorator import with_retry


class BaseScraper(ABC):
    """Clase base mejorada para todos los scrapers de instituciones"""
    
    def __init__(self, base_url: str, config: Dict, scraping_config):
        """Inicializa el scraper base"""
        # Normalizar URL base (eliminar / duplicadas y espacios)
        self.base_url = self._normalize_url(base_url.strip())
        self.config = config
        self.scraping_config = scraping_config
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = logging.getLogger(f"canarias_scraper.{self.__class__.__name__}")
        
        # Cache para robots.txt y URLs procesadas
        self.robots_cache = {}
        self.processed_urls = set()
        
        # Configurar sesión
        self._setup_session()
        
        # Verificar robots.txt si está habilitado
        if self.scraping_config.get('RESPECT_ROBOTS_TXT', True):
            self._check_robots_txt()
    
    def _normalize_url(self, url: str) -> str:
        """Normaliza una URL eliminando problemas comunes"""
        if not url:
            return url
        
        # Eliminar espacios y caracteres problemáticos
        url = url.strip().rstrip('/')
        
        # Asegurar protocolo
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Eliminar barras duplicadas en el path
        parsed = urlparse(url)
        path = parsed.path
        while '//' in path:
            path = path.replace('//', '/')
        
        # Reconstruir URL
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        if parsed.fragment:
            normalized += f"#{parsed.fragment}"
            
        return normalized
    
    def _setup_session(self):
        """Configura la sesión HTTP con headers apropiados"""
        try:
            # Headers mejorados
            default_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Usar headers de configuración si existen, sino usar defaults
            headers = getattr(self.scraping_config, 'DEFAULT_HEADERS', default_headers)
            self.session.headers.update(headers)
            
            # User-Agent inicial
            try:
                self.session.headers['User-Agent'] = self.ua.random
            except:
                self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            
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
            # Normalizar URL
            url = self._normalize_url(url)
            
            # Evitar URLs duplicadas en la misma sesión
            if url in self.processed_urls:
                self.logger.debug(f"URL ya procesada, saltando: {url}")
                return None
            
            # Verificar robots.txt
            if not self._can_fetch(url):
                self.logger.warning(f"Bloqueado por robots.txt: {url}")
                return None
            
            # Log de la petición
            self.logger.debug(f"Realizando petición {method}: {url}")
            
            # Rotar User-Agent ocasionalmente
            if hash(url) % 15 == 0:  # ~6.7% de las veces
                try:
                    self.session.headers['User-Agent'] = self.ua.random
                    self.logger.debug("User-Agent rotado")
                except:
                    pass  # Si falla el UserAgent, continuar
            
            # Preparar parámetros de la petición
            timeout = getattr(self.scraping_config, 'REQUEST_TIMEOUT', 30)
            request_params = {
                'timeout': timeout,
                'allow_redirects': True,
                'verify': True,  # Verificar certificados SSL
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
            
            # Agregar URL a procesadas
            self.processed_urls.add(url)
            
            # Log de respuesta exitosa
            self.logger.debug(f"Petición exitosa: {url} - Status: {response.status_code} - Size: {len(response.content)} bytes")
            
            # Respetar rate limiting
            delay = getattr(self.scraping_config, 'REQUEST_DELAY', 1)
            time.sleep(delay)
            
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
                rate_limit_delay = getattr(self.scraping_config, 'RATE_LIMIT_DELAY', 5)
                time.sleep(rate_limit_delay)
            raise
        except requests.exceptions.SSLError:
            self.logger.warning(f"Error SSL en: {url}")
            # Intentar sin verificación SSL como último recurso
            try:
                request_params['verify'] = False
                response = self.session.request(method, url, **request_params)
                response.raise_for_status()
                self.logger.debug(f"Petición exitosa sin verificación SSL: {url}")
                return response
            except:
                raise
        except Exception as e:
            self.logger.error(f"Error inesperado en petición {url}: {str(e)}")
            raise
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Parsea contenido HTML con BeautifulSoup"""
        try:
            # Usar parser más robusto
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
        except Exception as e:
            self.logger.error(f"Error parseando HTML: {str(e)}")
            # Intentar con parser alternativo
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                return soup
            except:
                # Parser básico como último recurso
                soup = BeautifulSoup(html_content, 'html5lib')
                return soup
    
    def _extract_document_info(self, link, base_url: str) -> Optional[Dict]:
        """Extrae información de un enlace a documento - VERSIÓN MEJORADA"""
        try:
            href = link.get('href', '')
            if not href:
                return None
            
            # Resolver URL completa
            full_url = self._resolve_url(href, base_url)
            if not full_url:
                return None
            
            # Verificar si es un documento válido
            if not self._is_valid_document_url(full_url):
                return None
            
            # Extraer información del enlace
            title = link.get_text(strip=True)
            if not title:
                title = link.get('title', link.get('aria-label', ''))
            
            # Limpiar título
            title = ' '.join(title.split())  # Normalizar espacios
            if len(title) > 200:  # Truncar títulos muy largos
                title = title[:197] + "..."
            
            # Información adicional del contexto
            description = self._extract_context_description(link)
            
            # Información básica del documento
            doc_info = {
                'url': full_url,
                'title': title or 'Documento sin título',
                'description': description,
                'source_url': base_url,
                'institution': self.__class__.__name__.replace('Scraper', ''),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'file_size': None,  # Se puede rellenar después
                'last_modified': None  # Se puede rellenar después
            }
            
            # Intentar extraer tipo de documento de la URL
            doc_type = self._extract_document_type(full_url)
            if doc_type:
                doc_info['document_type'] = doc_type
            
            # Intentar extraer más metadatos del enlace
            self._enrich_document_info(link, doc_info)
            
            return doc_info
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo info de documento: {str(e)}")
            return None
    
    def _extract_context_description(self, link) -> str:
        """Extrae descripción del contexto del enlace"""
        try:
            # Buscar descripción en elementos padre
            parent = link.parent
            description_parts = []
            
            # Buscar texto descriptivo cerca del enlace
            for _ in range(3):  # Hasta 3 niveles de padre
                if parent is None:
                    break
                
                # Buscar texto en hermanos
                for sibling in parent.find_all(text=True):
                    text = sibling.strip()
                    if text and len(text) > 10 and text.lower() not in link.get_text().lower():
                        description_parts.append(text)
                
                parent = parent.parent
            
            # Combinar y limpiar descripción
            description = ' '.join(description_parts[:2])  # Máximo 2 fragmentos
            description = ' '.join(description.split())  # Normalizar espacios
            
            return description[:300] if len(description) > 300 else description
            
        except:
            return ""
    
    def _enrich_document_info(self, link, doc_info: Dict):
        """Enriquece la información del documento con metadatos adicionales"""
        try:
            # Atributos adicionales del enlace
            if link.get('data-size'):
                doc_info['file_size'] = link.get('data-size')
            
            if link.get('data-modified'):
                doc_info['last_modified'] = link.get('data-modified')
            
            # Información de clases CSS para categorización
            css_classes = link.get('class', [])
            if css_classes:
                doc_info['css_classes'] = ' '.join(css_classes)
            
            # Información del contenedor padre para contexto
            parent_classes = []
            parent = link.parent
            for _ in range(2):  # 2 niveles de padre
                if parent and hasattr(parent, 'get'):
                    classes = parent.get('class', [])
                    if classes:
                        parent_classes.extend(classes)
                    parent = parent.parent
                else:
                    break
            
            if parent_classes:
                doc_info['parent_classes'] = ' '.join(parent_classes[:5])  # Limitar
                
        except Exception as e:
            self.logger.debug(f"Error enriqueciendo info de documento: {str(e)}")
    
    def _is_valid_document_url(self, url: str) -> bool:
        """Verifica si una URL corresponde a un documento válido - MEJORADO"""
        try:
            # Extensiones de documentos válidos
            valid_extensions = [
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.odt', '.ods', '.odp', '.rtf', '.txt', '.zip', '.rar'
            ]
            
            url_lower = url.lower()
            
            # Verificar extensión directa
            if any(url_lower.endswith(ext) for ext in valid_extensions):
                return True
            
            # Verificar extensión con parámetros
            if any(ext in url_lower for ext in valid_extensions):
                return True
            
            # Verificar patrones en la URL que indiquen documentos
            doc_patterns = [
                'documento', 'formulario', 'modelo', 'impreso', 'download',
                'descargar', 'archivo', 'file', 'attachment', 'media',
                'solicitud', 'certificado', 'informe', 'guia', 'manual'
            ]
            
            if any(pattern in url_lower for pattern in doc_patterns):
                return True
            
            # Verificar patrones en parámetros de URL
            if any(param in url_lower for param in ['?file=', '&file=', 'filename=', 'document=']):
                return True
            
            return False
            
        except Exception:
            return False
    
    def _extract_document_type(self, url: str) -> Optional[str]:
        """Extrae el tipo de documento de la URL - MEJORADO"""
        try:
            url_lower = url.lower()
            
            # Mapeo de extensiones a tipos
            type_mapping = {
                '.pdf': 'PDF',
                '.doc': 'Word', '.docx': 'Word',
                '.xls': 'Excel', '.xlsx': 'Excel',
                '.ppt': 'PowerPoint', '.pptx': 'PowerPoint',
                '.odt': 'OpenDocument Text',
                '.ods': 'OpenDocument Spreadsheet', 
                '.odp': 'OpenDocument Presentation',
                '.rtf': 'Rich Text Format',
                '.txt': 'Texto plano',
                '.zip': 'Archivo ZIP', '.rar': 'Archivo RAR'
            }
            
            for ext, doc_type in type_mapping.items():
                if ext in url_lower:
                    return doc_type
            
            return None
            
        except Exception:
            return None
    
    def _resolve_url(self, href: str, base_url: str) -> str:
        """Resuelve URL relativa a absoluta - MEJORADO"""
        try:
            if not href:
                return ""
            
            # Limpiar href
            href = href.strip()
            
            # Si ya es absoluta, normalizarla
            if href.startswith(('http://', 'https://')):
                return self._normalize_url(href)
            
            # Si es protocolo relativo
            if href.startswith('//'):
                parsed_base = urlparse(base_url)
                return self._normalize_url(f"{parsed_base.scheme}:{href}")
            
            # URL relativa normal
            resolved = urljoin(base_url, href)
            return self._normalize_url(resolved)
            
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
            doc_title = doc.get('title', '').lower()
            doc_url = doc.get('url', '').lower()
            
            # Verificar si coincide con algún tipo solicitado
            match = False
            for dt in doc_types:
                dt_lower = dt.lower()
                if (dt_lower in doc_type or 
                    dt_lower in doc_title or 
                    dt_lower in doc_url):
                    match = True
                    break
            
            if match:
                filtered.append(doc)
        
        return filtered
    
    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """Elimina documentos duplicados basándose en URL - MEJORADO"""
        seen_urls = set()
        unique_docs = []
        
        for doc in documents:
            url = doc.get('url', '')
            if not url:
                continue
            
            # Normalizar URL para comparación
            normalized_url = self._normalize_url(url)
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_docs.append(doc)
                
        return unique_docs
    
    def validate_config(self) -> bool:
        """Valida la configuración del scraper - MEJORADO"""
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
            
            # Verificar conectividad básica
            try:
                response = self._make_request(self.base_url)
                if response and response.status_code == 200:
                    self.logger.info(f"Conectividad verificada: {self.base_url}")
                else:
                    self.logger.warning(f"Problemas de conectividad con: {self.base_url}")
                    
            except Exception as e:
                self.logger.warning(f"No se pudo verificar conectividad: {e}")
            
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