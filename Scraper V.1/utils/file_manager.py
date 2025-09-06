"""
Gestor de archivos y descargas mejorado
Versión optimizada con mejor manejo de errores y validación
"""

import os
import hashlib
import requests
import mimetypes
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, Set
import logging
import json
from datetime import datetime


class FileManager:
    """Gestor avanzado de archivos y descargas"""
    
    # Mapeo de extensiones a tipos MIME
    MIME_EXTENSIONS = {
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/plain': '.txt',
        'application/rtf': '.rtf',
        'text/csv': '.csv'
    }
    
    def __init__(self, output_dir: str):
        """Inicializa el gestor de archivos"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("canarias_scraper.file_manager")
        
        # Cache de hashes descargados
        self.downloaded_hashes: Set[str] = set()
        self.failed_downloads: Set[str] = set()
        
        # Estadísticas
        self.stats = {
            'downloads_attempted': 0,
            'downloads_successful': 0,
            'downloads_failed': 0,
            'bytes_downloaded': 0,
            'cache_hits': 0
        }
        
        # Cargar estado existente
        self._load_existing_state()
    
    def generate_hash(self, url: str, title: str = "") -> str:
        """Genera hash único para un documento basado en URL y título"""
        # Combinar URL y título para mejor unicidad
        content = f"{url.lower().strip()}|{title.lower().strip()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_file_extension(self, url: str, content_type: str = None) -> str:
        """Obtiene la extensión de archivo de una URL con fallbacks inteligentes"""
        try:
            # 1. Intentar desde la URL
            parsed_url = urlparse(url)
            path = unquote(parsed_url.path)
            
            if path:
                _, ext = os.path.splitext(path)
                if ext and len(ext) <= 6:  # Extensión razonable
                    return ext.lower()
            
            # 2. Usar content-type si se proporcionó
            if content_type:
                ext = self.MIME_EXTENSIONS.get(content_type.split(';')[0].strip())
                if ext:
                    return ext
            
            # 3. Hacer HEAD request para obtener content-type
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    ext = self.MIME_EXTENSIONS.get(content_type.split(';')[0].strip())
                    if ext:
                        return ext
                    
                    # Usar mimetypes como fallback
                    ext = mimetypes.guess_extension(content_type.split(';')[0])
                    if ext:
                        return ext
            except:
                pass
            
            # 4. Analizar parámetros de la URL
            if 'pdf' in url.lower():
                return '.pdf'
            elif any(term in url.lower() for term in ['doc', 'word']):
                return '.doc'
            elif any(term in url.lower() for term in ['xls', 'excel']):
                return '.xls'
            
            return '.unknown'
            
        except Exception as e:
            self.logger.debug(f"Error determinando extensión para {url}: {e}")
            return '.unknown'
    
    def document_exists(self, doc_hash: str) -> bool:
        """Verifica si un documento ya fue descargado exitosamente"""
        return doc_hash in self.downloaded_hashes
    
    def download_failed_before(self, doc_hash: str) -> bool:
        """Verifica si un documento falló previamente"""
        return doc_hash in self.failed_downloads
    
    def download_document(self, url: str, category: str, doc_hash: str, 
                         title: str = "", max_size_mb: int = 50) -> Optional[str]:
        """Descarga un documento con validación completa y manejo de errores"""
        self.stats['downloads_attempted'] += 1
        
        try:
            # Verificaciones previas
            if self.document_exists(doc_hash):
                self.stats['cache_hits'] += 1
                self.logger.debug(f"Documento ya existe: {doc_hash}")
                return self._get_existing_file_path(doc_hash, category)
            
            if self.download_failed_before(doc_hash):
                self.logger.debug(f"Documento falló previamente: {doc_hash}")
                return None
            
            # Realizar descarga
            self.logger.info(f"Descargando: {url}")
            
            # Configurar request con validación de tamaño
            response = requests.get(
                url, 
                timeout=30, 
                stream=True,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Validar content-type
            content_type = response.headers.get('content-type', '').lower()
            if not self._is_valid_content_type(content_type):
                self.logger.warning(f"Content-type no válido: {content_type}")
                self.failed_downloads.add(doc_hash)
                return None
            
            # Validar tamaño
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    self.logger.warning(f"Archivo demasiado grande: {size_mb:.1f}MB")
                    self.failed_downloads.add(doc_hash)
                    return None
            
            # Determinar nombre y ruta del archivo
            file_ext = self.get_file_extension(url, content_type)
            filename = self._generate_filename(doc_hash, title, file_ext)
            
            # Crear directorio de categoría
            category_dir = self.output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = category_dir / filename
            
            # Descargar con control de tamaño
            downloaded_size = 0
            max_size_bytes = max_size_mb * 1024 * 1024
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Verificar tamaño durante la descarga
                        if downloaded_size > max_size_bytes:
                            self.logger.warning(f"Descarga excede límite: {downloaded_size/1024/1024:.1f}MB")
                            file_path.unlink(missing_ok=True)  # Eliminar archivo parcial
                            self.failed_downloads.add(doc_hash)
                            return None
            
            # Validar archivo descargado
            if not self._validate_downloaded_file(file_path, file_ext):
                file_path.unlink(missing_ok=True)
                self.failed_downloads.add(doc_hash)
                return None
            
            # Registrar descarga exitosa
            self.downloaded_hashes.add(doc_hash)
            self.stats['downloads_successful'] += 1
            self.stats['bytes_downloaded'] += downloaded_size
            
            relative_path = file_path.relative_to(self.output_dir)
            self.logger.info(f"Descarga exitosa: {relative_path} ({downloaded_size/1024:.1f}KB)")
            
            return str(relative_path)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error de red descargando {url}: {str(e)}")
            self.failed_downloads.add(doc_hash)
        except IOError as e:
            self.logger.error(f"Error de E/S descargando {url}: {str(e)}")
            self.failed_downloads.add(doc_hash)
        except Exception as e:
            self.logger.error(f"Error inesperado descargando {url}: {str(e)}")
            self.failed_downloads.add(doc_hash)
        
        self.stats['downloads_failed'] += 1
        return None
    
    def _is_valid_content_type(self, content_type: str) -> bool:
        """Valida si el content-type corresponde a un documento válido"""
        valid_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument',
            'application/vnd.ms-excel',
            'text/plain',
            'application/rtf',
            'text/csv'
        ]
        
        return any(valid_type in content_type for valid_type in valid_types)
    
    def _generate_filename(self, doc_hash: str, title: str, file_ext: str) -> str:
        """Genera un nombre de archivo limpio y válido"""
        try:
            if title:
                # Limpiar título para usar como nombre
                import re
                clean_title = re.sub(r'[^\w\s-]', '', title).strip()
                clean_title = re.sub(r'[-\s]+', '_', clean_title)
                
                if clean_title and len(clean_title) > 3:
                    # Limitar longitud
                    clean_title = clean_title[:50]
                    return f"{clean_title}_{doc_hash[:8]}{file_ext}"
            
            # Fallback: solo hash
            return f"doc_{doc_hash[:12]}{file_ext}"
            
        except:
            return f"{doc_hash}{file_ext}"
    
    def _validate_downloaded_file(self, file_path: Path, expected_ext: str) -> bool:
        """Valida que el archivo descargado sea válido"""
        try:
            # Verificar que el archivo existe y no está vacío
            if not file_path.exists() or file_path.stat().st_size == 0:
                return False
            
            # Validaciones específicas por tipo
            if expected_ext == '.pdf':
                return self._validate_pdf(file_path)
            elif expected_ext in ['.doc', '.docx']:
                return self._validate_office_doc(file_path)
            
            # Para otros tipos, verificar que no sea HTML de error
            return not self._is_error_page(file_path)
            
        except Exception as e:
            self.logger.debug(f"Error validando archivo {file_path}: {e}")
            return False
    
    def _validate_pdf(self, file_path: Path) -> bool:
        """Valida que un archivo sea un PDF válido"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
                return header == b'%PDF-'
        except:
            return False
    
    def _validate_office_doc(self, file_path: Path) -> bool:
        """Valida documentos de Office básicamente"""
        try:
            # Verificar que no comience con HTML
            with open(file_path, 'rb') as f:
                start = f.read(100).lower()
                return b'<html' not in start and b'<!doctype' not in start
        except:
            return False
    
    def _is_error_page(self, file_path: Path) -> bool:
        """Detecta si el archivo es una página de error HTML"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1000).lower()
                error_indicators = [
                    b'<html', b'<!doctype', b'<head>', b'error 404',
                    b'not found', b'access denied', b'forbidden'
                ]
                return any(indicator in content for indicator in error_indicators)
        except:
            return True  # Si no podemos leer, asumir error
    
    def _get_existing_file_path(self, doc_hash: str, category: str) -> Optional[str]:
        """Busca la ruta de un archivo existente"""
        category_dir = self.output_dir / category
        
        if not category_dir.exists():
            return None
        
        # Buscar archivos que contengan el hash
        for file_path in category_dir.iterdir():
            if doc_hash in file_path.name:
                return str(file_path.relative_to(self.output_dir))
        
        return None
    
    def _load_existing_state(self):
        """Carga el estado de descargas previas"""
        metadata_file = self.output_dir / "metadata.jsonl"
        failed_file = self.output_dir / "failed_downloads.json"
        
        # Cargar hashes de documentos exitosos
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            doc = json.loads(line.strip())
                            if doc.get('local_path'):
                                self.downloaded_hashes.add(doc['document_id'])
                        except json.JSONDecodeError:
                            self.logger.debug(f"Error parseando línea {line_num} en metadata.jsonl")
                
                self.logger.info(f"Cargados {len(self.downloaded_hashes)} documentos existentes")
                
            except Exception as e:
                self.logger.warning(f"Error cargando metadata existente: {e}")
        
        # Cargar descargas fallidas
        if failed_file.exists():
            try:
                with open(failed_file, 'r', encoding='utf-8') as f:
                    failed_data = json.load(f)
                    self.failed_downloads = set(failed_data.get('failed_hashes', []))
                
                self.logger.info(f"Cargadas {len(self.failed_downloads)} descargas fallidas")
                
            except Exception as e:
                self.logger.debug(f"Error cargando descargas fallidas: {e}")
    
    def save_failed_downloads(self):
        """Guarda la lista de descargas fallidas"""
        if not self.failed_downloads:
            return
        
        failed_file = self.output_dir / "failed_downloads.json"
        
        try:
            failed_data = {
                'failed_hashes': list(self.failed_downloads),
                'last_updated': datetime.now().isoformat(),
                'count': len(self.failed_downloads)
            }
            
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(failed_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error guardando descargas fallidas: {e}")
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas de descarga"""
        success_rate = 0
        if self.stats['downloads_attempted'] > 0:
            success_rate = (self.stats['downloads_successful'] / 
                          self.stats['downloads_attempted']) * 100
        
        return {
            **self.stats,
            'success_rate_percent': round(success_rate, 2),
            'total_documents': len(self.downloaded_hashes),
            'failed_documents': len(self.failed_downloads)
        }
    
    def cleanup_empty_directories(self):
        """Limpia directorios vacíos"""
        try:
            for category_dir in self.output_dir.iterdir():
                if category_dir.is_dir() and not any(category_dir.iterdir()):
                    category_dir.rmdir()
                    self.logger.debug(f"Directorio vacío eliminado: {category_dir}")
        except Exception as e:
            self.logger.debug(f"Error limpiando directorios: {e}")