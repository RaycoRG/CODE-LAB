from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class HaciendaCanariasScraper(BaseScraper):
    """Scraper específico para la Agencia Tributaria - Canarias"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos de Hacienda Canarias"""
        documents = []
        
        try:
            # Página principal
            response = self._make_request(self.base_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            
            # Buscar enlaces a secciones de documentos
            section_links = self._find_section_links(soup)
            
            # Procesar cada sección
            for section_url, section_name in section_links:
                self.logger.info(f"Procesando sección: {section_name}")
                
                section_docs = self._scrape_section(section_url)
                documents.extend(section_docs)
            
            # También buscar documentos en la página principal
            main_docs = self._get_document_links(soup, self.base_url)
            documents.extend(main_docs)
            
        except Exception as e:
            self.logger.error(f"Error scrapeando Hacienda Canarias: {str(e)}")
        
        self.logger.info(f"Hacienda Canarias: {len(documents)} documentos encontrados")
        return documents
    
    def _find_section_links(self, soup: BeautifulSoup) -> List[tuple]:
        """Encuentra enlaces a secciones de documentos"""
        section_links = []
        
        # Buscar enlaces que contengan palabras clave de documentos
        keywords = ['modelo', 'impreso', 'formulario', 'declaracion', 'liquidacion']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in keywords):
                href = link['href']
                full_url = self._resolve_url(href)
                section_links.append((full_url, link.get_text(strip=True)))
        
        return section_links[:10]  # Limitar a 10 secciones principales
    
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
        """Extrae enlaces a documentos PDF/DOC"""
        documents = []
        
        # Buscar enlaces directos a documentos
        for link in soup.find_all('a', href=True):
            doc_info = self._extract_document_info(link, base_url)
            if doc_info:
                documents.append(doc_info)
        
        return documents
    
    def _resolve_url(self, href: str) -> str:
        """Resuelve URL relativa a absoluta"""
        from urllib.parse import urljoin
        return urljoin(self.base_url, href)