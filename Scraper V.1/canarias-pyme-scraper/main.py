"""
Sistema principal de scraping para documentación PYME Canarias
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import Counter

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import ScrapingConfig
from utils.logger_setup import setup_logging
from utils.file_manager import FileManager
from institution_scrapers.scraper_factory import ScraperFactory
from utils.document_categorizer import DocumentCategorizer


class CanariasPYMEScraper:
    """Sistema principal de scraping para documentación PYME Canarias"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Inicializa el sistema de scraping"""
        self.config = ScrapingConfig(config_path)
        
        # Validar configuración
        if not self.config.validate_config():
            raise ValueError("Configuración inválida")
        
        # Crear directorios necesarios
        self.config.create_directories()
        
        # Configurar logging
        self.logger = setup_logging(self.config.LOG_LEVEL)
        
        # Inicializar componentes
        self.file_manager = FileManager(self.config.OUTPUT_DIR)
        self.categorizer = DocumentCategorizer()
        self.scraped_documents = []
        
        # Estadísticas
        self.stats = {
            'start_time': datetime.now(),
            'institutions_processed': 0,
            'documents_found': 0,
            'documents_downloaded': 0,
            'errors': 0
        }
    
    def run_scraping(self, institutions: Optional[List[str]] = None, 
                    doc_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ejecuta el proceso de scraping completo"""
        self.logger.info("Iniciando sistema de scraping PYME Canarias")
        self.logger.info(f"Configuración: {len(self.config.TARGET_SOURCES)} instituciones disponibles")
        
        # Configurar instituciones a procesar
        target_institutions = self._get_target_institutions(institutions)
        
        self.logger.info(f"Procesando {len(target_institutions)} instituciones")
        
        for institution in target_institutions:
            try:
                self._process_institution(institution, doc_types)
            except Exception as e:
                self.logger.error(f"Error crítico procesando {institution}: {str(e)}")
                self.stats['errors'] += 1
                continue
        
        # Generar resultados finales
        results = self._finalize_scraping()
        self.logger.info("Scraping completado exitosamente")
        
        return results
    
    def _get_target_institutions(self, institutions: Optional[List[str]]) -> List[str]:
        """Obtiene la lista de instituciones a procesar ordenadas por prioridad"""
        if institutions:
            # Filtrar instituciones válidas
            valid_institutions = [inst for inst in institutions 
                                if inst in self.config.TARGET_SOURCES]
            invalid = set(institutions) - set(valid_institutions)
            if invalid:
                self.logger.warning(f"Instituciones inválidas ignoradas: {invalid}")
            return valid_institutions
        
        # Ordenar por prioridad
        all_institutions = list(self.config.TARGET_SOURCES.items())
        sorted_institutions = sorted(all_institutions, 
                                   key=lambda x: x[1].get('priority', 999))
        
        return [inst[0] for inst in sorted_institutions]
    
    def _process_institution(self, institution: str, doc_types: Optional[List[str]]):
        """Procesa una institución específica"""
        self.logger.info(f"Procesando institución: {institution}")
        
        try:
            # Crear scraper específico
            institution_config = self.config.TARGET_SOURCES[institution]
            scraper = ScraperFactory.create_scraper(
                institution, 
                institution_config,
                self.config
            )
            
            # Ejecutar scraping
            documents = scraper.scrape_documents(doc_types)
            self.stats['documents_found'] += len(documents)
            
            # Procesar documentos obtenidos
            processed_count = 0
            for doc in documents:
                processed_doc = self._process_document(doc, institution)
                if processed_doc:
                    self.scraped_documents.append(processed_doc)
                    processed_count += 1
                    
                    # Límite por institución
                    max_docs = self.config.get('MAX_DOCUMENTS_PER_INSTITUTION', 50)
                    if processed_count >= max_docs:
                        self.logger.info(f"Alcanzado límite de {max_docs} documentos para {institution}")
                        break
            
            self.stats['institutions_processed'] += 1
            self.logger.info(f"{institution}: {processed_count} documentos procesados")
            
        except Exception as e:
            self.logger.error(f"Error procesando institución {institution}: {str(e)}")
            self.stats['errors'] += 1
            raise
    
    def _process_document(self, doc_data: Dict[str, Any], institution: str) -> Optional[Dict[str, Any]]:
        """Procesa y categoriza un documento individual"""
        try:
            # Validar datos mínimos
            if not doc_data.get('download_url') or not doc_data.get('title'):
                self.logger.debug("Documento sin URL o título, saltando")
                return None
            
            # Categorizar documento
            category = self.categorizer.categorize(
                doc_data.get('title', ''),
                doc_data.get('description', '')
            )
            
            # Generar ID único
            doc_hash = self.file_manager.generate_hash(doc_data['download_url'])
            
            # Verificar deduplicación
            if (self.config.get('ENABLE_DEDUPLICATION', True) and 
                self.file_manager.document_exists(doc_hash)):
                self.logger.debug(f"Documento duplicado saltado: {doc_hash}")
                return None
            
            # Crear estructura de documento
            processed_doc = {
                "document_id": doc_hash,
                "title": doc_data.get('title', '').strip(),
                "institution": institution,
                "document_type": doc_data.get('type', 'Desconocido'),
                "category": category,
                "download_url": doc_data['download_url'],
                "local_path": None,
                "description": doc_data.get('description', ''),
                "source_url": doc_data.get('source_url', ''),
                "metadata": {
                    "publication_date": doc_data.get('publication_date'),
                    "last_updated": datetime.now().isoformat(),
                    "file_type": self.file_manager.get_file_extension(doc_data['download_url']),
                    "file_size": doc_data.get('file_size'),
                    "language": doc_data.get('language', 'es')
                }
            }
            
            # Intentar descargar documento
            if self._should_download(processed_doc):
                local_path = self.file_manager.download_document(
                    doc_data['download_url'], 
                    category, 
                    processed_doc['document_id']
                )
                
                if local_path:
                    processed_doc['local_path'] = local_path
                    self.stats['documents_downloaded'] += 1
                else:
                    self.logger.warning(f"Fallo en descarga: {doc_data['download_url']}")
            
            return processed_doc
            
        except Exception as e:
            self.logger.error(f"Error procesando documento: {str(e)}")
            return None
    
    def _should_download(self, doc: Dict[str, Any]) -> bool:
        """Determina si un documento debe ser descargado"""
        # Verificar extensión válida
        file_ext = doc['metadata'].get('file_type', '').lower()
        if file_ext not in self.config.VALID_EXTENSIONS:
            self.logger.debug(f"Extensión no válida: {file_ext}")
            return False
        
        # Verificar URL válida
        if not doc['download_url'].startswith(('http://', 'https://')):
            self.logger.debug(f"URL no válida: {doc['download_url']}")
            return False
        
        return True
    
    def _finalize_scraping(self) -> Dict[str, Any]:
        """Finaliza el proceso de scraping y genera resúmenes"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        # Generar estadísticas
        categories = Counter(doc['category'] for doc in self.scraped_documents)
        institutions = Counter(doc['institution'] for doc in self.scraped_documents)
        doc_types = Counter(doc['document_type'] for doc in self.scraped_documents)
        
        summary = {
            'execution_info': {
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'config_used': dict(self.config.config)
            },
            'statistics': {
                'total_documents': len(self.scraped_documents),
                'documents_downloaded': self.stats['documents_downloaded'],
                'institutions_processed': self.stats['institutions_processed'],
                'errors': self.stats['errors']
            },
            'breakdown': {
                'by_category': dict(categories),
                'by_institution': dict(institutions),
                'by_document_type': dict(doc_types)
            }
        }
        
        # Guardar metadatos
        self._save_metadata()
        
        # Guardar resumen
        self._save_summary(summary)
        
        # Log final
        self.logger.info(f"Scraping finalizado: {len(self.scraped_documents)} documentos en {duration}")
        self.logger.info(f"Por categoría: {dict(categories)}")
        
        return summary
    
    def _save_metadata(self):
        """Guarda metadatos de documentos en formato JSONL"""
        metadata_file = Path(self.config.OUTPUT_DIR) / "metadata.jsonl"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                for doc in self.scraped_documents:
                    json.dump(doc, f, ensure_ascii=False)
                    f.write('\n')
            
            self.logger.info(f"Metadatos guardados: {metadata_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando metadatos: {e}")
    
    def _save_summary(self, summary: Dict[str, Any]):
        """Guarda resumen de ejecución"""
        summary_file = Path(self.config.OUTPUT_DIR) / "summary.json"
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Resumen guardado: {summary_file}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resumen: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Sistema de scraping para documentación PYME Canarias",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Ruta al archivo de configuración personalizada'
    )
    
    parser.add_argument(
        '--institutions', '-i',
        nargs='+',
        help='Instituciones específicas a procesar'
    )
    
    parser.add_argument(
        '--doc-types', '-t',
        nargs='+',
        help='Tipos de documentos específicos a buscar'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Habilitar modo verboso (DEBUG)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Ejecutar sin descargar documentos (solo análisis)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Directorio de salida personalizado'
    )
    
    return parser


def main():
    """Función principal"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Crear instancia del scraper
        scraper = CanariasPYMEScraper(args.config)
        
        # Aplicar configuraciones de argumentos
        if args.verbose:
            scraper.config.set('LOG_LEVEL', 'DEBUG')
            scraper.logger.setLevel(logging.DEBUG)
        
        if args.output_dir:
            scraper.config.set('OUTPUT_DIR', args.output_dir)
            scraper.config.create_directories()
        
        if args.dry_run:
            scraper.logger.info("Modo DRY-RUN activado - no se descargarán archivos")
            scraper.config.set('ENABLE_DOWNLOAD', False)
        
        # Mostrar configuración
        scraper.logger.info("Configuración del sistema:")
        scraper.logger.info(f"  Directorio de salida: {scraper.config.OUTPUT_DIR}")
        scraper.logger.info(f"  Nivel de log: {scraper.config.LOG_LEVEL}")
        scraper.logger.info(f"  Máx. reintentos: {scraper.config.MAX_RETRIES}")
        scraper.logger.info(f"  Timeout: {scraper.config.REQUEST_TIMEOUT}s")
        
        # Ejecutar scraping
        results = scraper.run_scraping(
            institutions=args.institutions,
            doc_types=args.doc_types
        )
        
        # Mostrar resultados
        print("\n" + "="*50)
        print("RESUMEN DE EJECUCIÓN")
        print("="*50)
        print(f"Documentos encontrados: {results['statistics']['total_documents']}")
        print(f"Documentos descargados: {results['statistics']['documents_downloaded']}")
        print(f"Instituciones procesadas: {results['statistics']['institutions_processed']}")
        print(f"Errores: {results['statistics']['errors']}")
        print(f"Duración: {results['execution_info']['duration_seconds']:.2f} segundos")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
        return 1
    except Exception as e:
        print(f"Error crítico: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())