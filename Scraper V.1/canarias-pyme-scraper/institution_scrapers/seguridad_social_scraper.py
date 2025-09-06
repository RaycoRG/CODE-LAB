# institution_scrapers/seguridad_social_scraper.py - Scraper para Seguridad Social
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class SeguridadSocialScraper(BaseScraper):
    """Scraper específico para Seguridad Social - Canarias"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos de Seguridad Social"""
        documents = []
        
        try:
            # Áreas específicas de Seguridad Social
            areas = self.config.get('areas', ['autonomos', 'empresas', 'cotizacion'])
            
            for area in areas:
                self.logger.info(f"Procesando área SS: {area}")
                area_docs = self._scrape_ss_area(area)
                documents.extend(area_docs)
                
        except Exception as e:
            self.logger.error(f"Error scrapeando Seguridad Social: {str(e)}")
        
        self.logger.info(f"Seguridad Social: {len(documents)} documentos encontrados")
        return documents
    
    def _scrape_ss_area(self, area: str) -> List[Dict]:
        """Scrapea un área específica de la Seguridad Social"""
        documents = []
        
        try:
            # Construir URLs específicas para cada área
            area_urls = {
                'autonomos': f"{self.base_url.rstrip('/')}/autonomos/",
                'empresas': f"{self.base_url.rstrip('/')}/empresas/",
                'cotizacion': f"{self.base_url.rstrip('/')}/cotizacion/"
            }
            
            area_url = area_urls.get(area, self.base_url)
            
            response = self._make_request(area_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            
            # Buscar secciones de documentación
            doc_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                term in str(x).lower() for term in ['documento', 'formulario', 'modelo', 'descarga']
            ))
            
            for section in doc_sections:
                section_docs = self._get_document_links(section, area_url)
                documents.extend(section_docs)
                
        except Exception as e:
            self.logger.warning(f"Error en área SS {area}: {str(e)}")
        
        return documents
    
    def _get_document_links(self, soup_element, base_url: str) -> List[Dict]:
        """Extrae enlaces a documentos de la Seguridad Social"""
        documents = []
        
        for link in soup_element.find_all('a', href=True):
            doc_info = self._extract_document_info(link, base_url)
            if doc_info:
                # Añadir información específica de SS
                doc_info['institution_type'] = 'seguridad_social'
                documents.append(doc_info)
        
        return documents
