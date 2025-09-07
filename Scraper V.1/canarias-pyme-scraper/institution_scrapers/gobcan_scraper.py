# institution_scrapers/gobcan_scraper.py - VERSIÓN MEJORADA
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re


class GobcanScraper(BaseScraper):
    """Scraper específico para Gobierno de Canarias - VERSIÓN MEJORADA"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos del Gobierno de Canarias"""
        documents = []
        
        try:
            self.logger.info("Iniciando scraping de Gobierno de Canarias")
            
            # Verificar configuración
            if not self.validate_config():
                self.logger.error("Configuración inválida para GobCan")
                return documents
            
            # Estrategia múltiple
            documents.extend(self._scrape_main_gobcan_page())
            documents.extend(self._scrape_gobcan_areas())
            documents.extend(self._scrape_tramites_section())
            documents.extend(self._scrape_ayudas_section())
            
            # Filtrar por tipo si se especifica
            if doc_types:
                documents = self._filter_documents_by_type(documents, doc_types)
            
            # Deduplicar
            documents = self._deduplicate_documents(documents)
            
        except Exception as e:
            self.logger.error(f"Error scrapeando Gobierno de Canarias: {str(e)}")
        
        self.logger.info(f"Gobierno de Canarias: {len(documents)} documentos encontrados")
        return documents
    
    def _scrape_main_gobcan_page(self) -> List[Dict]:
        """Scrapea la página principal"""
        documents = []
        
        try:
            self.logger.info("Scrapeando página principal de GobCan")
            response = self._make_request(self.base_url)
            
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._extract_gobcan_documents(soup, self.base_url)
            
            self.logger.info(f"Documentos en página principal GobCan: {len(documents)}")
            
        except Exception as e:
            self.logger.warning(f"Error en página principal GobCan: {str(e)}")
        
        return documents
    
    def _scrape_gobcan_areas(self) -> List[Dict]:
        """Scrapea áreas específicas del Gobierno de Canarias"""
        documents = []
        
        # Áreas conocidas con URLs que funcionan
        gobcan_areas = [
            {
                'name': 'Economía y Hacienda',
                'urls': [
                    'https://www.gobiernodecanarias.org/hacienda/',
                    'https://www.gobiernodecanarias.org/economia/',
                    'https://www3.gobiernodecanarias.org/aplicaciones/unifica/Presupuestos2025.html',
                    'https://www.gobiernodecanarias.org/economia/promocioneconomica/info_empresarial_new'
                ]
            },
            {
                'name': 'Empleo',
                'urls': [
                    'https://www.gobiernodecanarias.org/empleo/',
                    'https://www.gobiernodecanarias.org/empleo/sce/principal/areas_tematicas/empleo/index.html',
                    'https://www.gobiernodecanarias.org/empleo/sce/principal/componentes/index.html',
                ]
            },
            {
                'name': 'Industria y Comercio',
                'urls': [
                    'https://www.gobiernodecanarias.org/industria',
                    'https://www.gobiernodecanarias.org/comercio',
                    'https://www.gobiernodecanarias.org/economia',
                ]
            },
            {
                'name': 'Turismo',
                'urls': [
                    'https://www.gobiernodecanarias.org/turismo/',
                    'https://turismodecanarias.com/',
                ]
            },
            {
                'name': 'Agricultura y Desarrollo Rural',
                'urls': [
                    'https://www.gobiernodecanarias.org/agricultura/',
                    'https://www.gobiernodecanarias.org/pesca'
                ]
            },
            {
                'name': 'Medio Ambiente',
                'urls': [
                    'https://www.gobiernodecanarias.org/medioambiente/',
                    'https://sede.gobiernodecanarias.org/sede/procedimientos_servicios/tramites/5927'
                ]
            }
        ]
        
        # También usar las áreas de configuración si existen
        config_areas = self.config.get('areas', [])
        if config_areas:
            for area in config_areas:
                try:
                    area_url = self._build_area_url(area)
                    area_docs = self._scrape_gobcan_area_url(area_url, area)
                    documents.extend(area_docs)
                except Exception as e:
                    self.logger.debug(f"Error en área de config {area}: {str(e)}")
        
        # Procesar áreas conocidas
        for area in gobcan_areas:
            self.logger.info(f"Procesando área GobCan: {area['name']}")
            
            for url in area['urls']:
                try:
                    area_docs = self._scrape_gobcan_area_url(url, area['name'])
                    documents.extend(area_docs)
                    
                except Exception as e:
                    self.logger.debug(f"Error en área {area['name']} - URL {url}: {str(e)}")
                    continue
        
        return documents
    
    def _build_area_url(self, area: str) -> str:
        """Construye URL de área a partir del nombre"""
        try:
            # Limpiar nombre de área
            clean_area = area.lower().strip().replace(' ', '')
            
            # Mapeo de nombres a URLs
            area_mapping = {
                'economia': 'economia',
                'empleo': 'empleo', 
                'industria': 'economia/industriaycomercio',
                'turismo': 'turismo',
                'agricultura': 'agricultura',
                'medioambiente': 'medioambiente',
                'hacienda': 'hacienda'
            }
            
            area_path = area_mapping.get(clean_area, clean_area)
            return f"{self.base_url.rstrip('/')}/{area}/"
            
    def _scrape_gobcan_area_url(self, url: str, area_name: str) -> List[Dict]:
        """Scrapea una URL específica de área GobCan"""
        documents = []
        
        try:
            self.logger.debug(f"Accediendo a área GobCan: {url}")
            response = self._make_request(url)
            
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._extract_gobcan_documents(soup, url, area_name)
            
            # También buscar en subsecciones importantes
            subsections = self._find_important_subsections(soup, url)
            for subsection_url, subsection_name in subsections:
                try:
                    sub_docs = self._scrape_gobcan_subsection(subsection_url, f"{area_name} - {subsection_name}")
                    documents.extend(sub_docs)
                except Exception as e:
                    self.logger.debug(f"Error en subsección {subsection_url}: {str(e)}")
            
            self.logger.debug(f"Área GobCan {area_name}: {len(documents)} documentos")
            
        except Exception as e:
            self.logger.debug(f"Error procesando área GobCan {area_name}: {str(e)}")
        
        return documents
    
    def _find_important_subsections(self, soup: BeautifulSoup, base_url: str) -> List[tuple]:
        """Encuentra subsecciones importantes para empresas"""
        subsections = []
        
        try:
            # Keywords para subsecciones importantes
            important_keywords = [
                'tramites', 'procedimientos', 'formularios', 'documentos',
                'empresas', 'ayudas', 'subvenciones', 'licencias',
                'permisos', 'autorizaciones', 'registros', 'certificados'
            ]
            
            # Buscar enlaces en menús de navegación
            nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'menu|nav|sidebar', re.I))
            
            for nav in nav_elements:
                links = nav.find_all('a', href=True)
                for link in links:
                    text = link.get_text(strip=True).lower()
                    if any(keyword in text for keyword in important_keywords):
                        href = link['href']
                        full_url = self._resolve_url(href, base_url)
                        if full_url.startswith(base_url[:30]):  # Mismo dominio aproximadamente
                            subsections.append((full_url, link.get_text(strip=True)))
            
            # Limitar subsecciones para evitar demasiadas peticiones
            return subsections[:5]
            
        except Exception as e:
            self.logger.debug(f"Error buscando subsecciones: {str(e)}")
            return []
    
    def _scrape_gobcan_subsection(self, url: str, section_name: str) -> List[Dict]:
        """Scrapea una subsección específica"""
        documents = []
        
        try:
            response = self._make_request(url)
            if response:
                soup = self._parse_html(response.text)
                documents = self._extract_gobcan_documents(soup, url, section_name)
                
        except Exception as e:
            self.logger.debug(f"Error en subsección {url}: {str(e)}")
        
        return documents
    
    def _scrape_tramites_section(self) -> List[Dict]:
        """Scrapea sección específica de trámites"""
        documents = []
        
        try:
            # URLs conocidas de trámites del Gobierno de Canarias
            tramites_urls = [
                'https://sede.gobiernodecanarias.org/sede/procedimientos_servicios/tramites',
                'https://sede.gobiernodecanarias.org/sede/',
                'https://sede.gobiernodecanarias.org/sede/tramites'
            ]
            
            for tramites_url in tramites_urls:
                try:
                    self.logger.info(f"Buscando trámites en: {tramites_url}")
                    response = self._make_request(tramites_url)
                    
                    if response:
                        soup = self._parse_html(response.text)
                        tramites_docs = self._extract_tramites_documents(soup, tramites_url)
                        documents.extend(tramites_docs)
                        
                except Exception as e:
                    self.logger.debug(f"Error en sección trámites {tramites_url}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error en sección de trámites: {str(e)}")
        
        return documents
    
    def _scrape_ayudas_section(self) -> List[Dict]:
        """Scrapea sección específica de ayudas y subvenciones"""
        documents = []
        
        try:
            # URLs de ayudas y subvenciones
            ayudas_urls = [
                'https://sede.gobiernodecanarias.org/sede/procedimientos_servicios/tramites?',
                'https://www.gobiernodecanarias.org/economia/promocioneconomica/subvenciones',
                'https://www.gobiernodecanarias.org/economia/europedirect/becas_cursos_practicas'
            ]
            
            for ayudas_url in ayudas_urls:
                try:
                    self.logger.info(f"Buscando ayudas en: {ayudas_url}")
                    response = self._make_request(ayudas_url)
                    
                    if response:
                        soup = self._parse_html(response.text)
                        ayudas_docs = self._extract_ayudas_documents(soup, ayudas_url)
                        documents.extend(ayudas_docs)
                        
                except Exception as e:
                    self.logger.debug(f"Error en sección ayudas {ayudas_url}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error en sección de ayudas: {str(e)}")
        
        return documents
    
    def _extract_gobcan_documents(self, soup: BeautifulSoup, base_url: str, area_name: str = None) -> List[Dict]:
        """Extrae documentos específicos del Gobierno de Canarias"""
        documents = []
        
        try:
            # Selectores específicos para GobCan
            doc_selectors = [
                'div.documento', 'div.archivo', 'div.descarga',
                'div.formulario', 'div.modelo', 'div.impreso',
                'a[href*=".pdf"]', 'a[href*=".doc"]', 'a[href*=".xls"]',
                'a[href*="descargar"]', 'a[href*="documento"]',
                'a[href*="formulario"]', 'a[href*="modelo"]'
            ]
            
            found_elements = []
            for selector in doc_selectors:
                try:
                    elements = soup.select(selector)
                    found_elements.extend(elements)
                except:
                    continue
            
            # Buscar también en contenido principal
            main_content = soup.find(['main', 'div'], {'id': re.compile(r'content|main|principal', re.I)})
            if main_content:
                main_links = main_content.find_all('a', href=True)
                found_elements.extend(main_links)
            
            # Si no encontramos nada específico, buscar todos los enlaces
            if not found_elements:
                found_elements = soup.find_all('a', href=True)
            
            self.logger.debug(f"Elementos encontrados para análisis GobCan: {len(found_elements)}")
            
            for element in found_elements:
                if element.name == 'a':
                    doc_info = self._extract_gobcan_document_info(element, base_url, area_name)
                    if doc_info:
                        documents.append(doc_info)
                else:
                    # Si es contenedor, buscar enlaces dentro
                    links = element.find_all('a', href=True)
                    for link in links:
                        doc_info = self._extract_gobcan_document_info(link, base_url, area_name)
                        if doc_info:
                            documents.append(doc_info)
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo documentos GobCan: {str(e)}")
        
        return documents
    
    def _extract_tramites_documents(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae documentos específicos de trámites"""
        documents = []
        
        try:
            # Buscar formularios de trámites
            tramite_containers = soup.find_all(['div', 'section'], 
                                             class_=re.compile(r'tramite|procedimiento|formulario', re.I))
            
            for container in tramite_containers:
                links = container.find_all('a', href=True)
                for link in links:
                    doc_info = self._extract_gobcan_document_info(link, base_url, 'Trámites')
                    if doc_info:
                        doc_info['document_category'] = 'Trámite Administrativo'
                        documents.append(doc_info)
            
            # También buscar en listas de trámites
            tramite_lists = soup.find_all(['ul', 'ol'], class_=re.compile(r'tramite|lista', re.I))
            for list_elem in tramite_lists:
                items = list_elem.find_all('li')
                for item in items:
                    links = item.find_all('a', href=True)
                    for link in links:
                        doc_info = self._extract_gobcan_document_info(link, base_url, 'Trámites')
                        if doc_info:
                            doc_info['document_category'] = 'Trámite Administrativo'
                            documents.append(doc_info)
                            
        except Exception as e:
            self.logger.debug(f"Error extrayendo documentos de trámites: {str(e)}")
        
        return documents
    
    def _extract_ayudas_documents(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae documentos específicos de ayudas y subvenciones"""
        documents = []
        
        try:
            # Buscar contenedores de ayudas
            ayuda_containers = soup.find_all(['div', 'section'], 
                                           class_=re.compile(r'ayuda|subvencion|convocatoria', re.I))
            
            for container in ayuda_containers:
                links = container.find_all('a', href=True)
                for link in links:
                    doc_info = self._extract_gobcan_document_info(link, base_url, 'Ayudas y Subvenciones')
                    if doc_info:
                        doc_info['document_category'] = 'Ayuda/Subvención'
                        documents.append(doc_info)
            
            # Buscar tablas de convocatorias (común en páginas de ayudas)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        links = cell.find_all('a', href=True)
                        for link in links:
                            doc_info = self._extract_gobcan_document_info(link, base_url, 'Ayudas y Subvenciones')
                            if doc_info:
                                doc_info['document_category'] = 'Convocatoria'
                                documents.append(doc_info)
                                
        except Exception as e:
            self.logger.debug(f"Error extrayendo documentos de ayudas: {str(e)}")
        
        return documents
    
    def _extract_gobcan_document_info(self, link, base_url: str, area_name: str = None) -> Optional[Dict]:
        """Extrae información específica de documentos del Gobierno de Canarias"""
        try:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Filtros específicos para GobCan
            gobcan_keywords = [
                'modelo', 'formulario', 'solicitud', 'impreso',
                'certificado', 'documento', 'guia', 'manual',
                'tramite', 'procedimiento', 'ayuda', 'subvencion',
                'convocatoria', 'bases', 'anexo', 'orden',
                'resolucion', 'decreto', 'ley', 'reglamento'
            ]
            
            # Verificar relevancia
            is_relevant = (
                any(keyword in text for keyword in gobcan_keywords) or
                any(keyword in href.lower() for keyword in gobcan_keywords) or
                self._is_valid_document_url(href) or
                # Patrones específicos de normativa canaria
                re.search(r'(boc|decreto|ley\s+\d+|orden\s+de)', text, re.I)
            )
            
            if not is_relevant:
                return None
            
            # Usar método base para extracción básica
            doc_info = super()._extract_document_info(link, base_url)
            if not doc_info:
                return None
            
            # Enriquecimientos específicos para GobCan
            if area_name:
                doc_info['area'] = area_name
            
            # Detectar tipo de documento GobCan
            if any(word in text for word in ['decreto', 'ley', 'orden', 'resolucion']):
                doc_info['document_type_gobcan'] = 'Normativa'
            elif any(word in text for word in ['convocatoria', 'bases']):
                doc_info['document_type_gobcan'] = 'Convocatoria'
            elif any(word in text for word in ['modelo', 'formulario', 'solicitud']):
                doc_info['document_type_gobcan'] = 'Formulario'
            elif any(word in text for word in ['guia', 'manual', 'instrucciones']):
                doc_info['document_type_gobcan'] = 'Guía/Manual'
            elif any(word in text for word in ['certificado', 'informe']):
                doc_info['document_type_gobcan'] = 'Certificado/Informe'
            
            # Detectar sector específico
            if any(word in text for word in ['turismo', 'turistico', 'hotel']):
                doc_info['sector'] = 'Turismo'
            elif any(word in text for word in ['industria', 'industrial', 'fabrica']):
                doc_info['sector'] = 'Industria'
            elif any(word in text for word in ['comercio', 'comercial', 'tienda']):
                doc_info['sector'] = 'Comercio'
            elif any(word in text for word in ['agricultura', 'agricola', 'rural']):
                doc_info['sector'] = 'Agricultura'
            elif any(word in text for word in ['energia', 'energetico', 'renovable']):
                doc_info['sector'] = 'Energía'
            
            # Detectar audiencia objetivo
            if any(word in text for word in ['empresa', 'empresario', 'empleador', 'pyme']):
                doc_info['target_audience'] = 'Empresas'
            elif any(word in text for word in ['autonomo', 'freelance']):
                doc_info['target_audience'] = 'Autónomos'
            elif any(word in text for word in ['ciudadano', 'particular']):
                doc_info['target_audience'] = 'Ciudadanos'
            
            # Detectar si es BOC (Boletín Oficial de Canarias)
            if 'boc' in text or 'boc' in href.lower():
                doc_info['publication'] = 'BOC'
                doc_info['document_type_gobcan'] = 'Normativa BOC'
            
            doc_info['institution_type'] = 'gobierno_canarias'
            
            return doc_info
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo info documento GobCan: {str(e)}")
            return Nonestrip('/')}/{area_path}/"
            
        except Exception as e:
            self.logger.debug(f"Error construyendo URL para área {area}: {str(e)}")
            return f"{self.base_url.r