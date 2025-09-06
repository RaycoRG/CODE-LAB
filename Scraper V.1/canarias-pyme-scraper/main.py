# main.py - Script principal del sistema de scraping
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import ScrapingConfig
from utils.logger_setup import setup_logging
from utils.file_manager import FileManager
from institution_scrapers.scraper_factory import ScraperFactory
from utils.document_categorizer import DocumentCategorizer


class CanariasPYMEScraper:
    """Sistema principal de scraping para documentación PYME Canarias"""
    
    def __init__(self, config_path=None):
        self.config = ScrapingConfig(config_path)
        self.logger = setup_logging(self.config.LOG_LEVEL)
        self.file_manager = FileManager(self.config.OUTPUT_DIR)
        self.categorizer = DocumentCategorizer()
        self.scraped_documents = []
        
    def run_scraping(self, institutions=None, doc_types=None):
        """Ejecuta el proceso de scraping completo"""
        self.logger.info("Iniciando sistema de scraping PYME Canarias")
        
        # Configurar instituciones a scrapear
        target_institutions = institutions or list(self.config.TARGET_SOURCES.keys())
        
        for institution in target_institutions:
            self.logger.info(f"Procesando institución: {institution}")
            
            try:
                # Crear scraper específico
                scraper = ScraperFactory.create_scraper(
                    institution, 
                    self.config.TARGET_SOURCES[institution],
                    self.config
                )
                
                # Ejecutar scraping
                documents = scraper.scrape_documents(doc_types)
                
                # Procesar documentos obtenidos
                for doc in documents:
                    processed_doc = self._process_document(doc, institution)
                    if processed_doc:
                        self.scraped_documents.append(processed_doc)
                        
            except Exception as e:
                self.logger.error(f"Error procesando {institution}: {str(e)}")
                continue
        
        # Guardar resultados
        self._save_results()
        self.logger.info(f"Scraping completado. {len(self.scraped_documents)} documentos procesados")
    
    def _process_document(self, doc_data, institution):
        """Procesa y categoriza un documento individual"""
        try:
            # Categorizar documento
            category = self.categorizer.categorize(doc_data.get('title', ''))
            
            # Crear estructura de documento
            processed_doc = {
                "document_id": self.file_manager.generate_hash(doc_data['download_url']),
                "title": doc_data.get('title', ''),
                "institution": institution,
                "document_type": doc_data.get('type', 'Desconocido'),
                "category": category,
                "download_url": doc_data['download_url'],
                "local_path": None,
                "metadata": {
                    "publication_date": doc_data.get('publication_date'),
                    "last_updated": datetime.now().isoformat(),
                    "file_type": self.file_manager.get_file_extension(doc_data['download_url'])
                }
            }
            
            # Descargar documento si es válido
            if self._should_download(processed_doc):
                local_path = self.file_manager.download_document(
                    doc_data['download_url'], 
                    category, 
                    processed_doc['document_id']
                )
                processed_doc['local_path'] = local_path
                
            return processed_doc
            
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