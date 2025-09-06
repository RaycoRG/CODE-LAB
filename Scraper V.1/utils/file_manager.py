import os
import hashlib
import requests
import mimetypes
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional
import logging

class FileManager:
    """Gestor de archivos y descargas"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger("canarias_scraper.file_manager")
        self.downloaded_hashes = set()
        
        # Cargar hashes de documentos ya descargados
        self._load_existing_hashes()
    
    def generate_hash(self, url: str) -> str:
        """Genera hash único para una URL"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def get_file_extension(self, url: str) -> str:
        """Obtiene la extensión de archivo de una URL"""
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        
        # Intentar obtener extensión del path
        _, ext = os.path.splitext(path)
        
        if ext:
            return ext
        
        # Si no hay extensión, intentar determinar por content-type
        try:
            response = requests.head(url, timeout=10)
            content_type = response.headers.get('content-type', '')
            ext = mimetypes.guess_extension(content_type.split(';')[0])
            return ext or '.unknown'
        except:
            return '.unknown'
    
    def document_exists(self, doc_hash: str) -> bool:
        """Verifica si un documento ya fue descargado"""
        return doc_hash in self.downloaded_hashes
    
    def download_document(self, url: str, category: str, doc_hash: str) -> Optional[str]:
        """Descarga un documento y lo guarda en la estructura de directorios"""
        try:
            # Verificar si ya existe
            if self.document_exists(doc_hash):
                self.logger.debug(f"⏭Documento ya descargado: {doc_hash}")
                return None
            
            # Realizar descarga
            self.logger.info(f"Descargando: {url}")
            
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Determinar nombre y ruta del archivo
            file_ext = self.get_file_extension(url)
            filename = f"{doc_hash}{file_ext}"
            
            # Crear ruta completa
            category_dir = self.output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = category_dir / filename
            
            # Guardar archivo
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Registrar descarga
            self.downloaded_hashes.add(doc_hash)
            
            self.logger.info(f"Descargado: {file_path}")
            return str(file_path.relative_to(self.output_dir))
            
        except Exception as e:
            self.logger.error(f"Error descargando {url}: {str(e)}")
            return None
    
    def _load_existing_hashes(self):
        """Carga hashes de documentos ya descargados"""
        metadata_file = self.output_dir / "metadata.jsonl"
        
        if metadata_file.exists():
            try:
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        doc = json.loads(line.strip())
                        if doc.get('local_path'):
                            self.downloaded_hashes.add(doc['document_id'])
                            
                self.logger.info(f"📚 Cargados {len(self.downloaded_hashes)} hashes existentes")
                
            except Exception as e:
                self.logger.warning(f"Error cargando hashes existentes: {e}")