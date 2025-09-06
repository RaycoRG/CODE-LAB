# institution_scrapers/cabildo_scraper.py - Scraper para Cabildos
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class CabildoScraper(BaseScraper):
    """Scraper para páginas de Cabildos insulares"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos de Cabildos"""
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
                self.logger.info(f"Procesando: {section_name}")
                section_docs = self._scrape_section(section_url)
                documents.extend(section_docs)
                
        except Exception as e:
            self.logger.error(f"Error scrapeando Cabildo: {str(e)}")
        
        self.logger.info(f"Cabildo: {len(documents)} documentos encontrados")
        return documents
    
    def _find_business_sections(self, soup: BeautifulSoup) -> List[tuple]:
        """Encuentra secciones relacionadas con empresas"""
        sections = []
        
        # Keywords para identificar secciones empresariales
        keywords = ['empresa', 'empleo', 'economia', 'desarrollo', 'subvencion', 
                   'ayuda', 'tramite', 'licencia', 'actividad']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in keywords):
                href = link['href']
                full_url = self._resolve_url(href)
                sections.append((full_url, link.get_text(strip=True)))
        
        return sections[:8]  # Limitar secciones
    
    def _scrape_section(self, section_url: str) -> List[Dict]:
        """Scrapea una sección específica"""
        documents = []
        
        try:
            response = self._make_request(section_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._get_document_links(soup, section_url)
            
        except Exception as e:
            self.logger.warning(f"Error en sección {section_url}: {str(e)}")
        
        return documents
    
    def _get_document_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extrae enlaces a documentos"""
        documents = []
        
        for link in soup.find_all('a', href=True):
            doc_info = self._extract_document_info(link, base_url)
            if doc_info:
                documents.append(doc_info)
        
        return documents
    
    def _resolve_url(self, href: str) -> str:
        """Resuelve URL relativa a absoluta"""
        from urllib.parse import urljoin
        return urljoin(self.base_url, href)