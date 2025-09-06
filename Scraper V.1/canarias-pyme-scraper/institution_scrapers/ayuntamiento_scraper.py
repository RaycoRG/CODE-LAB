# institution_scrapers/ayuntamiento_scraper.py - Scraper para Ayuntamientos
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class AyuntamientoScraper(BaseScraper):
    """Scraper para páginas de Ayuntamientos"""
    
    def scrape_documents(self, doc_types: Optional[List[str]] = None) -> List[Dict]:
        """Scrapea documentos de Ayuntamientos"""
        documents = []
        
        try:
            # Buscar páginas de tramitación empresarial
            tramite_urls = self._find_tramite_pages()
            
            for url, page_name in tramite_urls:
                self.logger.info(f"Procesando: {page_name}")
                page_docs = self._scrape_tramite_page(url)
                documents.extend(page_docs)
                
        except Exception as e:
            self.logger.error(f"Error scrapeando Ayuntamiento: {str(e)}")
        
        self.logger.info(f"Ayuntamiento: {len(documents)} documentos encontrados")
        return documents
    
    def _find_tramite_pages(self) -> List[tuple]:
        """Encuentra páginas de trámites empresariales"""
        pages = []
        
        try:
            response = self._make_request(self.base_url)
            if not response:
                return pages
            
            soup = self._parse_html(response.text)
            
            # Keywords para trámites empresariales
            keywords = ['licencia', 'tramite', 'empresa', 'actividad', 'apertura',
                       'municipal', 'impuesto', 'tasa', 'registro']
            
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True).lower()
                if any(keyword in text for keyword in keywords):
                    href = link['href']
                    full_url = self._resolve_url(href)
                    pages.append((full_url, link.get_text(strip=True)))
                    
        except Exception as e:
            self.logger.warning(f"Error buscando páginas de trámites: {str(e)}")
        
        return pages[:6]  # Limitar a 6 páginas principales
    
    def _scrape_tramite_page(self, page_url: str) -> List[Dict]:
        """Scrapea una página de trámites específica"""
        documents = []
        
        try:
            response = self._make_request(page_url)
            if not response:
                return documents
            
            soup = self._parse_html(response.text)
            documents = self._get_document_links(soup, page_url)
            
        except Exception as e:
            self.logger.warning(f"Error en página {page_url}: {str(e)}")
        
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