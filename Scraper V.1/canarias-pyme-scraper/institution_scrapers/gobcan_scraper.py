# institution_scrapers/gobcan_scraper.py - Scraper para Gobierno de Canarias
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class GobcanScraper(BaseScraper):
    """Scraper específico para Gobierno de Canarias"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos del Gobierno de Canarias"""
        documents = []
        
        try:
            # Áreas de interés para PYMEs
            target_areas = self.config.get('areas', [])
            
            for area in target_areas:
                self.logger.info(f"Procesando área: {area}")
                
                # Construir URL del área
                area_url = f"{self.base_url.rstrip('/')}/{area.lstrip('/')}/"
                area_docs = self._scrape_area(area_url, area)
                documents.extend(area_docs)
                
        except Exception as e:
            self.logger.error(f"Error scrapeando Gobierno de Canarias: {str(e)}")
        
        self.logger.info(f"Gobierno de Canarias: {len(documents)} documentos encontrados")
        return documents
    
    def _scrape_area(self, area_url: str, area_name: str) -> List[Dict]:
        """Scrapea un área específica"""
        documents = []
        
        try:
            response = self._make_request(area_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            
            # Buscar secciones de documentación
            doc_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                term in x.lower() for term in ['documento', 'descarga', 'archivo', 'pdf']
            ))
            
            for section in doc_sections:
                section_docs = self._get_document_links(section, area_url)
                for doc in section_docs:
                    doc['area'] = area_name
                documents.extend(section_docs)
                
        except Exception as e:
            self.logger.warning(f"Error en área {area_name}: {str(e)}")
        
        return documents
    
    def _get_document_links(self, soup_element, base_url: str) -> List[Dict]:
        """Extrae enlaces a documentos de un elemento"""
        documents = []
        
        for link in soup_element.find_all('a', href=True):
            doc_info = self._extract_document_info(link, base_url)
            if doc_info:
                documents.append(doc_info)
        
        return documents