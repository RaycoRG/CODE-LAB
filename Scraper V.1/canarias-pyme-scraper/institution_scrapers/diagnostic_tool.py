# diagnostic_tool.py - Herramienta de diagnóstico para scrapers
"""
Herramienta de diagnóstico para identificar problemas en scrapers
Ayuda a verificar conectividad, analizar páginas web y detectar elementos de documentos
"""

import requests
import logging
import sys
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
from typing import List, Dict, Optional
import json


class ScrapingDiagnostic:
    """Herramienta de diagnóstico para scrapers"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.ua.random
        })
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("diagnostic")
    
    def diagnose_url(self, url: str) -> Dict:
        """Diagnóstica una URL específica"""
        results = {
            'url': url,
            'connectivity': False,
            'status_code': None,
            'content_length': 0,
            'content_type': None,
            'redirects': [],
            'errors': [],
            'document_analysis': {},
            'recommendations': []
        }
        
        try:
            self.logger.info(f"Diagnosticando URL: {url}")
            
            # Test de conectividad
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            results['connectivity'] = True
            results['status_code'] = response.status_code
            results['content_length'] = len(response.content)
            results['content_type'] = response.headers.get('content-type', 'unknown')
            
            # Registrar redirects
            if response.history:
                results['redirects'] = [r.url for r in response.history]
            
            # Verificar si la respuesta es exitosa
            response.raise_for_status()
            
            # Analizar contenido si es HTML
            if 'text/html' in results['content_type']:
                results['document_analysis'] = self._analyze_html_content(response.text, url)
            
        except requests.exceptions.Timeout:
            results['errors'].append("Timeout - la página tarda demasiado en responder")
            results['recommendations'].append("Aumentar el timeout en la configuración")
            
        except requests.exceptions.ConnectionError as e:
            results['errors'].append(f"Error de conexión: {str(e)}")
            results['recommendations'].append("Verificar que la URL sea correcta y accesible")
            
        except requests.exceptions.HTTPError as e:
            results['errors'].append(f"Error HTTP {e.response.status_code}: {str(e)}")
            if e.response.status_code == 404:
                results['recommendations'].append("La URL no existe - verificar la ruta")
            elif e.response.status_code == 403:
                results['recommendations'].append("Acceso denegado - revisar User-Agent o headers")
            elif e.response.status_code == 429:
                results['recommendations'].append("Rate limit excedido - reducir velocidad de requests")
                
        except Exception as e:
            results['errors'].append(f"Error inesperado: {str(e)}")
            
        return results
    
    def _analyze_html_content(self, html_content: str, base_url: str) -> Dict:
        """Analiza contenido HTML buscando documentos y problemas"""
        analysis = {
            'total_links': 0,
            'document_links': [],
            'potential_documents': [],
            'forms': [],
            'issues': [],
            'suggestions': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analizar enlaces
            all_links = soup.find_all('a', href=True)
            analysis['total_links'] = len(all_links)
            
            # Clasificar enlaces
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Resolver URL completa
                full_url = urljoin(base_url, href)
                
                # Verificar si es un documento
                if self._is_document_url(full_url):
                    analysis['document_links'].append({
                        'url': full_url,
                        'text': text,
                        'type': self._get_document_type(full_url)
                    })
                
                # Verificar si podría ser un documento
                elif self._could_be_document(text, href):
                    analysis['potential_documents'].append({
                        'url': full_url,
                        'text': text,
                        'reason': self._get_potential_reason(text, href)
                    })
            
            # Analizar formularios
            forms = soup.find_all('form')
            for form in forms:
                form_info = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'GET'),
                    'inputs': len(form.find_all('input'))
                }
                analysis['forms'].append(form_info)
            
            # Detectar problemas comunes
            analysis['issues'] = self._detect_issues(soup, base_url)
            
            # Generar sugerencias
            analysis['suggestions'] = self._generate_suggestions(analysis)
            
        except Exception as e:
            analysis['issues'].append(f"Error analizando HTML: {str(e)}")
        
        return analysis
    
    def _is_document_url(self, url: str) -> bool:
        """Verifica si una URL es claramente un documento"""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        url_lower = url.lower()
        return any(ext in url_lower for ext in doc_extensions)
    
    def _get_document_type(self, url: str) -> str:
        """Obtiene el tipo de documento de la URL"""
        url_lower = url.lower()
        if '.pdf' in url_lower:
            return 'PDF'
        elif '.doc' in url_lower:
            return 'Word'
        elif '.xls' in url_lower:
            return 'Excel'
        elif '.ppt' in url_lower:
            return 'PowerPoint'
        return 'Unknown'
    
    def _could_be_document(self, text: str, href: str) -> bool:
        """Verifica si podría ser un enlace a documento"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        doc_keywords = [
            'formulario', 'modelo', 'documento', 'descargar',
            'solicitud', 'impreso', 'certificado', 'guia',
            'manual', 'archivo', 'file'
        ]
        
        return any(keyword in text_lower or keyword in href_lower for keyword in doc_keywords)
    
    def _get_potential_reason(self, text: str, href: str) -> str:
        """Obtiene la razón por la que podría ser un documento"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        if 'formulario' in text_lower or 'formulario' in href_lower:
            return 'Contiene palabra "formulario"'
        elif 'documento' in text_lower or 'documento' in href_lower:
            return 'Contiene palabra "documento"'
        elif 'descargar' in text_lower or 'descargar' in href_lower:
            return 'Contiene palabra "descargar"'
        elif 'modelo' in text_lower or 'modelo' in href_lower:
            return 'Contiene palabra "modelo"'
        
        return 'Contiene keywords relacionadas con documentos'
    
    def _detect_issues(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Detecta problemas comunes en la página"""
        issues = []
        
        # Verificar si hay contenido JavaScript pesado
        scripts = soup.find_all('script')
        if len(scripts) > 20:
            issues.append("Página con mucho JavaScript - podría requerir renderizado")
        
        # Verificar enlaces rotos o problemáticos
        links = soup.find_all('a', href=True)
        broken_links = 0
        for link in links[:50]:  # Verificar solo los primeros 50
            href = link.get('href', '')
            if href.startswith('#') or href == '':
                broken_links += 1
        
        if broken_links > 10:
            issues.append(f"Muchos enlaces vacíos o de ancla ({broken_links})")
        
        # Verificar si hay indicios de SPA (Single Page Application)
        if soup.find(['div', 'section'], {'id': re.compile(r'app|root|main', re.I)}):
            spa_indicators = soup.find_all(['div'], class_=re.compile(r'react|vue|angular', re.I))
            if spa_indicators:
                issues.append("Posible SPA - podría requerir JavaScript para cargar contenido")
        
        return issues
    
    def _generate_suggestions(self, analysis: Dict) -> List[str]:
        """Genera sugerencias basadas en el análisis"""
        suggestions = []
        
        if analysis['document_links']:
            suggestions.append(f"✅ Se encontraron {len(analysis['document_links'])} enlaces directos a documentos")
        else:
            suggestions.append("⚠️  No se encontraron enlaces directos a documentos")
        
        if analysis['potential_documents']:
            suggestions.append(f"🔍 Se encontraron {len(analysis['potential_documents'])} enlaces potenciales a documentos")
            suggestions.append("💡 Revisar estos enlaces potenciales manualmente")
        
        if analysis['forms']:
            suggestions.append(f"📝 Se encontraron {len(analysis['forms'])} formularios - podrían contener documentos")
        
        if analysis['total_links'] == 0:
            suggestions.append("🚨 No se encontraron enlaces - verificar si la página carga correctamente")
        elif analysis['total_links'] < 10:
            suggestions.append("⚠️  Pocos enlaces encontrados - revisar si el contenido se carga dinámicamente")
        
        return suggestions
    
    def diagnose_scraper_config(self, config: Dict) -> Dict:
        """Diagnostica la configuración de un scraper"""
        results = {
            'config_valid': True,
            'issues': [],
            'recommendations': [],
            'url_tests': {}
        }
        
        # Verificar campos requeridos
        required_fields = ['base_url', 'scraper_class']
        for field in required_fields:
            if field not in config:
                results['config_valid'] = False
                results['issues'].append(f"Falta campo requerido: {field}")
        
        # Verificar URL base
        if 'base_url' in config:
            base_url = config['base_url']
            
            # Verificar formato de URL
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                results['config_valid'] = False
                results['issues'].append(f"URL base inválida: {base_url}")
            else:
                # Test de conectividad
                url_test = self.diagnose_url(base_url)
                results['url_tests']['base_url'] = url_test
                
                if not url_test['connectivity']:
                    results['issues'].append("No se puede conectar a la URL base")
                    results['recommendations'].extend(url_test['recommendations'])
        
        # Verificar áreas si existen
        if 'areas' in config:
            areas = config['areas']
            for area in areas[:3]:  # Solo las primeras 3 áreas
                area_url = f"{config['base_url'].rstrip('/')}/{area.lstrip('/')}/"
                area_test = self.diagnose_url(area_url)
                results['url_tests'][f'area_{area}'] = area_test
                
                if not area_test['connectivity']:
                    results['recommendations'].append(f"Área '{area}' no accesible")
        
        return results
    
    def run_comprehensive_diagnosis(self, institutions_config: Dict) -> Dict:
        """Ejecuta diagnóstico completo de todas las instituciones"""
        overall_results = {
            'timestamp': '',
            'total_institutions': len(institutions_config),
            'working_institutions': 0,
            'problematic_institutions': 0,
            'institution_results': {}
        }
        
        self.logger.info("Iniciando diagnóstico completo...")
        
        for institution_name, config in