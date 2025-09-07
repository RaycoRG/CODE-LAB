# institution_scrapers/sepe_scraper.py - VERSIÓN MEJORADA
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re


class SepeScraper(BaseScraper):
    """Scraper específico para SEPE - Canarias - VERSIÓN MEJORADA"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos del SEPE relacionados con empresas"""
        documents = []
        
        try:
            self.logger.info("Iniciando scraping de SEPE")
            
            # Verificar configuración
            if not self.validate_config():
                self.logger.error("Configuración inválida para SEPE")
                return documents
            
            # Estrategia múltiple
            documents.extend(self._scrape_main_sepe_page())
            documents.extend(self._scrape_sepe_areas())
            documents.extend(self._scrape_sepe_forms_section())
            
            # Filtrar por tipo si se especifica
            if doc_types:
                documents = self._filter_documents_by_type(documents, doc_types)
            
            # Deduplicar
            documents = self._deduplicate_documents(documents)
            
        except Exception as e:
            self.logger.error(f"Error scrapeando SEPE: {str(e)}")
        
        self.logger.info(f"SEPE: {len(documents)} documentos encontrados")
        return documents
    
    def _scrape_main_sepe_page(self) -> List[Dict]:
        """Scrapea la página principal del SEPE"""
        documents = []
        
        try:
            self.logger.info("Scrapeando página principal de SEPE")
            
            # URLs principales del SEPE que funcionan
            main_urls = [
                "https://www.sepe.es/",
                "https://www.sepe.es/HomeSepe/",
                "https://sede.sepe.gob.es/"
            ]
            
            for url in main_urls:
                try:
                    response = self._make_request(url)
                    if response:
                        soup = self._parse_html(response.text)
                        page_docs = self._extract_sepe_documents(soup, url)
                        documents.extend(page_docs)
                        
                        # Si encontramos documentos, usamos esta URL como base
                        if page_docs:
                            break
                            
                except Exception as e:
                    self.logger.debug(f"Error en URL principal {url}: {str(e)}")
                    continue
            
            self.logger.info(f"Documentos en página principal SEPE: {len(documents)}")
            
        except Exception as e:
            self.logger.warning(f"Error en página principal SEPE: {str(e)}")
        
        return documents
    
    def _scrape_sepe_areas(self) -> List[Dict]:
        """Scrapea áreas específicas del SEPE con URLs correctas"""
        documents = []
        
        # URLs conocidas que funcionan para SEPE
        sepe_areas = [
            {
                'name': 'Empresarios',
                'urls': [
                    'https://www.sepe.es/HomeSepe/empresas.html',
                    'https://www.sepe.es/HomeSepe/autonomos.html',
                    'https://www.sepe.es/HomeSepe/empresas.html'
                ]
            },
            {
                'name': 'Contratos',
                'urls': [
                    'https://sede.sepe.gob.es/portalSede/procedimientos-y-servicios/empresas/contratos.html',
                ]
            },
            {
                'name': 'Prestaciones',
                'urls': [
                    'https://www.sepe.es/HomeSepe/Personas/distributiva-prestaciones.html',
                    'https://www.sepe.es/HomeSepe/prestaciones-desempleo;jsessionid=428AAA9B6DF6A227748502D09D7C9E13.lxmaginterpro1a',
                ]
            },
            {
                'name': 'Bonificaciones',
                'urls': [
                    'https://www.sepe.es/HomeSepe/empresas/Contratos-de-trabajo/contrato-indefinido-personas-desempleadas-larga-duracion',
                    'https://www.sepe.es/HomeSepe/que-es-el-sepe/comunicacion-institucional/publicaciones/publicaciones-oficiales/listado-pub-empleo/bonificaciones-reducciones-contratacion-laboral'
                ]
                ]
            },
            {
                'name': 'Formación',
                'urls': [
                    'https://www.sepe.es/HomeSepe/formacion-trabajo.html',
            }
        ]
        
        for area in sepe_areas:
            self.logger.info(f"Procesando área SEPE: {area['name']}")
            
            for url in area['urls']:
                try:
                    area_docs = self._scrape_sepe_area_url(url, area['name'])
                    documents.extend(area_docs)
                    
                    # Si encontramos documentos, continuamos con otras URLs de esta área
                    # (no break como en SS, porque SEPE puede tener docs distribuidos)
                    
                except Exception as e:
                    self.logger.debug(f"Error en área {area['name']} - URL {url}: {str(e)}")
                    continue
        
        return documents
    
    def _scrape_sepe_area_url(self, url: str, area_name: str) -> List[Dict]:
        """Scrapea una URL específica de área SEPE"""
        documents = []
        
        try:
            self.logger.debug(f"Accediendo a área SEPE: {url}")
            response = self._make_request(url)
            
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._extract_sepe_documents(soup, url, area_name)
            
            self.logger.debug(f"Área SEPE {area_name}: {len(documents)} documentos")
            
        except Exception as e:
            self.logger.debug(f"Error procesando área SEPE {area_name}: {str(e)}")
        
        return documents
    
    def _scrape_sepe_forms_section(self) -> List[Dict]:
        """Scrapea sección específica de formularios del SEPE"""
        documents = []
        
        try:
            # URLs específicas de formularios
            forms_urls = [
                'https://www.sepe.es/HomeSepe/empresas/informacion-para-empresas.html',
                'https://sede.sepe.gob.es/portalSede/procedimientos-y-servicios/empresas/proteccion-por-desempleo.html'
            ]
            
            for forms_url in forms_urls:
                try:
                    self.logger.info(f"Buscando formularios en: {forms_url}")
                    response = self._make_request(forms_url)
                    
                    if response:
                        soup = self._parse_html(response.text)
                        forms_docs = self._extract_sepe_forms(soup, forms_url)
                        documents.extend(forms_docs)
                        
                except Exception as e:
                    self.logger.debug(f"Error en sección formularios {forms_url}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error en sección de formularios: {str(e)}")
        
        return documents
    
    def _extract_sepe_documents(self, soup: BeautifulSoup, base_url: str, area_name: str = None) -> List[Dict]:
        """Extrae documentos específicos del SEPE"""
        documents = []
        
        try:
            # Buscar contenedores de documentos específicos de SEPE
            doc_selectors = [
                # Selectores CSS específicos para SEPE
                'div.descarga',
                'div.documento', 
                'div.archivo',
                'div.formulario',
                'div.modelo',
                'a[href*=".pdf"]',
                'a[href*=".doc"]',
                'a[href*="descargar"]',
                'a[href*="formulario"]',
                'a[href*="modelo"]'
            ]
            
            found_elements = []
            for selector in doc_selectors:
                try:
                    elements = soup.select(selector)
                    found_elements.extend(elements)
                except:
                    continue
            
            # Si no encontramos elementos específicos, buscar todos los enlaces
            if not found_elements:
                found_elements = soup.find_all('a', href=True)
            
            self.logger.debug(f"Elementos encontrados para análisis: {len(found_elements)}")
            
            for element in found_elements:
                # Si es un enlace, procesarlo directamente
                if element.name == 'a':
                    doc_info = self._extract_sepe_document_info(element, base_url, area_name)
                    if doc_info:
                        documents.append(doc_info)
                else:
                    # Si es un contenedor, buscar enlaces dentro
                    links = element.find_all('a', href=True)
                    for link in links:
                        doc_info = self._extract_sepe_document_info(link, base_url, area_name)
                        if doc_info:
                            documents.append(doc_info)
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo documentos SEPE: {str(e)}")
        
        return documents
    
    def _extract_sepe_forms(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae formularios específicos del SEPE"""
        documents = []
        
        try:
            # Buscar tablas de formularios (común en SEPE)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        links = cell.find_all('a', href=True)
                        for link in links:
                            doc_info = self._extract_sepe_document_info(link, base_url, 'Formularios')
                            if doc_info:
                                documents.append(doc_info)
            
            # También buscar listas de formularios
            lists = soup.find_all(['ul', 'ol'])
            for list_elem in lists:
                items = list_elem.find_all('li')
                for item in items:
                    links = item.find_all('a', href=True)
                    for link in links:
                        doc_info = self._extract_sepe_document_info(link, base_url, 'Formularios')
                        if doc_info:
                            documents.append(doc_info)
                            
        except Exception as e:
            self.logger.debug(f"Error extrayendo formularios SEPE: {str(e)}")
        
        return documents
    
    def _extract_sepe_document_info(self, link, base_url: str, area_name: str = None) -> Optional[Dict]:
        """Extrae información específica de documentos SEPE"""
        try:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Filtros específicos para SEPE
            sepe_keywords = [
                'modelo', 'formulario', 'solicitud', 'impreso',
                'certificado', 'documento', 'guia', 'manual',
                'contrato', 'prestacion', 'desempleo', 'bonificacion',
                'subvencion', 'ayuda', 'formacion', 'curso'
            ]
            
            # Verificar relevancia
            is_relevant = (
                any(keyword in text for keyword in sepe_keywords) or
                any(keyword in href.lower() for keyword in sepe_keywords) or
                self._is_valid_document_url(href) or
                # Patrones específicos de códigos SEPE
                re.search(r'(ex-\d+|mod\.\s*\d+|modelo\s*\d+)', text, re.I)
            )
            
            if not is_relevant:
                return None
            
            # Usar método base para extracción básica
            doc_info = super()._extract_document_info(link, base_url)
            if not doc_info:
                return None
            
            # Enriquecimientos específicos para SEPE
            if area_name:
                doc_info['area'] = area_name
            
            # Detectar tipo de trámite SEPE
            if any(word in text for word in ['contrato', 'contratos']):
                doc_info['tramite_type'] = 'Contratos de Trabajo'
            elif any(word in text for word in ['prestacion', 'desempleo', 'paro']):
                doc_info['tramite_type'] = 'Prestaciones por Desempleo'
            elif any(word in text for word in ['bonificacion', 'reduccion', 'incentivo']):
                doc_info['tramite_type'] = 'Bonificaciones y Reducciones'
            elif any(word in text for word in ['formacion', 'curso', 'capacitacion']):
                doc_info['tramite_type'] = 'Formación para el Empleo'
            elif any(word in text for word in ['subvencion', 'ayuda']):
                doc_info['tramite_type'] = 'Ayudas y Subvenciones'
            
            # Detectar códigos de formulario SEPE
            code_match = re.search(r'(ex-\d+|mod\.\s*(\d+)|modelo\s*(\d+))', text, re.I)
            if code_match:
                doc_info['form_code'] = code_match.group(0)
            
            # Audiencia objetivo
            if any(word in text for word in ['empresa', 'empresario', 'empleador']):
                doc_info['target_audience'] = 'Empresas'
            elif any(word in text for word in ['trabajador', 'empleado']):
                doc_info['target_audience'] = 'Trabajadores'
            elif any(word in text for word in ['autonomo']):
                doc_info['target_audience'] = 'Autónomos'
            
            doc_info['institution_type'] = 'sepe'
            
            return doc_info
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo info documento SEPE: {str(e)}")
            return None