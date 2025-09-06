# institution_scrapers/sepe_scraper.py - Scraper para SEPE Canarias
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class SepeScraper(BaseScraper):
    """Scraper específico para SEPE - Canarias"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos del SEPE relacionados con empresas"""
        documents = []
        
        try:
            # Áreas específicas del SEPE
            sepe_areas = [
                "empresas/prestaciones-por-desempleo",
                "empresas/contratos-de-trabajo", 
                "empresas/bonificaciones-y-reducciones",
                "trabajadores/prestaciones"
            ]
            
            for area in sepe_areas:
                self.logger.info(f"Procesando área SEPE: {area}")
                area_docs = self._scrape_sepe_area(area)
                documents.extend(area_docs)
                
        except Exception as e:
            self.logger.error(f"Error scrapeando SEPE: {str(e)}")
        
        # Filtrar y deduplicar
        documents = self._filter_documents_by_type(documents, doc_types)
        documents = self._deduplicate_documents(documents)
        
        self.logger.info(f"SEPE: {len(documents)} documentos encontrados")
        return documents
    
    def _scrape_sepe_area(self, area: str) -> List[Dict]:
        """Scrapea un área específica del SEPE"""
        documents = []
        
        try:
            area_url = f"{self.base_url.rstrip('/')}/{area.strip('/')}/"
            
            response = self._make_request(area_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            
            # Buscar enlaces a documentos
            doc_links = soup.find_all('a', href=True)
            for link in doc_links:
                # Filtrar solo enlaces que parezcan documentos
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Keywords específicas del SEPE
                sepe_keywords = [
                    'modelo', 'formulario', 'solicitud', 'certificado',
                    'documento', 'impreso', 'guia', 'manual'
                ]
                
                if any(keyword in text or keyword in href.lower() 
                      for keyword in sepe_keywords):
                    doc_info = self._extract_document_info(link, area_url)
                    if doc_info:
                        documents.append(doc_info)
                        
        except Exception as e:
            self.logger.warning(f"Error en área SEPE {area}: {str(e)}")
        
        return documents
    
    def _get_document_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae enlaces a documentos del SEPE"""
        documents = []
        
        # Buscar en secciones específicas
        doc_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['documento', 'descarga', 'archivo']
        ))
        
        for section in doc_sections:
            for link in section.find_all('a', href=True):
                doc_info = self._extract_document_info(link, base_url)
                if doc_info:
                    documents.append(doc_info)
        
        return documents


# institution_scrapers/camara_comercio_scraper.py - Scraper para Cámaras de Comercio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class CamaraComercioScraper(BaseScraper):
    """Scraper para Cámaras de Comercio de Canarias"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos de las Cámaras de Comercio"""
        documents = []
        
        try:
            # Página principal
            response = self._make_request(self.base_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            
            # Buscar secciones empresariales
            business_sections = self._find_business_sections(soup)
            
            for section_url, section_name in business_sections:
                self.logger.info(f"Procesando sección: {section_name}")
                section_docs = self._scrape_section(section_url)
                documents.extend(section_docs)
                
            # También documentos de la página principal
            main_docs = self._get_document_links(soup, self.base_url)
            documents.extend(main_docs)
            
        except Exception as e:
            self.logger.error(f"Error scrapeando Cámara de Comercio: {str(e)}")
        
        # Filtrar y deduplicar
        documents = self._filter_documents_by_type(documents, doc_types)
        documents = self._deduplicate_documents(documents)
        
        self.logger.info(f"Cámara de Comercio: {len(documents)} documentos encontrados")
        return documents
    
    def _find_business_sections(self, soup: BeautifulSoup) -> List[tuple]:
        """Encuentra secciones relacionadas con empresas y emprendimiento"""
        sections = []
        
        # Keywords específicas para Cámaras de Comercio
        keywords = [
            'empresa', 'emprendimiento', 'creacion', 'constitucion',
            'tramite', 'servicios', 'comercio', 'internacional',
            'exportacion', 'formacion', 'certificado', 'documento'
        ]
        
        # Buscar enlaces en navegación y contenido
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            
            if any(keyword in text for keyword in keywords):
                href = link['href']
                full_url = self._resolve_url(href, self.base_url)
                sections.append((full_url, link.get_text(strip=True)))
        
        return sections[:10]  # Limitar a 10 secciones principales
    
    def _scrape_section(self, section_url: str) -> List[Dict]:
        """Scrapea una sección específica"""
        documents = []
        
        try:
            response = self._make_request(section_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._get_document_links(soup, section_url)
            
            # Buscar subsecciones
            subsections = soup.find_all('a', href=True)[:5]  # Limitar subsecciones
            for subsection_link in subsections:
                subsection_url = self._resolve_url(subsection_link['href'], section_url)
                
                # Evitar loops infinitos
                if subsection_url != section_url and subsection_url.startswith(self.base_url):
                    try:
                        sub_response = self._make_request(subsection_url)
                        if sub_response:
                            sub_soup = self._parse_html(sub_response.text)
                            sub_docs = self._get_document_links(sub_soup, subsection_url)
                            documents.extend(sub_docs)
                    except:
                        pass  # Fallos en subsecciones no son críticos
                        
        except Exception as e:
            self.logger.warning(f"Error en sección {section_url}: {str(e)}")
        
        return documents
    
    def _get_document_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae enlaces a documentos de la Cámara de Comercio"""
        documents = []
        
        # Buscar enlaces a documentos
        for link in soup.find_all('a', href=True):
            doc_info = self._extract_document_info(link, base_url)
            if doc_info:
                # Agregar información específica de Cámara de Comercio
                doc_info['institution_type'] = 'camara_comercio'
                documents.append(doc_info)
        
        return documents