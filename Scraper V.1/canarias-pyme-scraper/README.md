# Sistema de Scraping Modular - Documentación PYME Canarias

## Descripción

Sistema automatizado de scraping para recolectar documentación esencial para la creación de PYMEs en Canarias. Diseñado con arquitectura modular, manejo inteligente de errores y categorización automática de documentos.

## Características Principales

- **Arquitectura Modular**: Scrapers especializados por institución
- **Gestión Inteligente**: Rotación de user-agents y delays adaptativos  
- **Manejo Robusto de Errores**: Sistema de reintentos con exponential backoff
- **Categorización Automática**: Clasificación temática de documentos
- **Deduplicación**: Evita descargas duplicadas mediante hashing
- **Logging Extensivo**: Monitorización completa del proceso

## Estructura del Proyecto

```
canarias-pyme-scraper/
├── main.py                     # Script principal
├── requirements.txt            # Dependencias
├── setup.py                   # Instalación opcional
├── README.md                  # Documentación
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuración centralizada
├── utils/
│   ├── __init__.py
│   ├── logger_setup.py        # Sistema de logging
│   ├── file_manager.py        # Gestión de archivos
│   ├── document_categorizer.py # Categorizador automático
│   └── retry_decorator.py     # Decorador de reintentos
├── institution_scrapers/
│   ├── __init__.py
│   ├── base_scraper.py        # Clase base
│   ├── scraper_factory.py     # Factory pattern
│   ├── hacienda_scraper.py    # Hacienda Canarias
│   ├── gobcan_scraper.py      # Gobierno de Canarias
│   ├── cabildo_scraper.py     # Cabildos insulares
│   ├── ayuntamiento_scraper.py # Ayuntamientos
│   └── seguridad_social_scraper.py # Seguridad Social
├── documents/                 # Directorio de salida
│   ├── fiscal/
│   ├── laboral/
│   ├── municipal/
│   ├── autonomico/
│   ├── general/
│   ├── metadata.jsonl        # Metadatos estructurados
│   └── summary.json          # Resumen de ejecución
└── logs/                     # Logs del sistema
```

## Instalación

### Requisitos Previos
- Python 3.11 o superior
- pip (gestor de paquetes)

### Instalación Rápida

```bash
# Clonar o descargar el proyecto
cd canarias-pyme-scraper

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Instalación como Paquete (Opcional)

```bash
pip install -e .
```

## Configuración

### Configuración Básica

El sistema funciona con configuración por defecto, pero puedes personalizar creando `config/custom_config.json`:

```json
{
    "OUTPUT_DIR": "./mi_directorio_docs",
    "LOG_LEVEL": "DEBUG",
    "MAX_RETRIES": 5,
    "REQUEST_TIMEOUT": 45,
    "DELAY_BETWEEN_REQUESTS": 3
}
```

### Variables de Entorno (Opcional)

```bash
export SCRAPER_LOG_LEVEL=INFO
export SCRAPER_OUTPUT_DIR=./documents
export SCRAPER_MAX_RETRIES=3
```

## Uso

### Uso Básico

```bash
# Ejecutar scraping completo
python main.py

# Modo verboso
python main.py --verbose

# Instituciones específicas
python main.py --institutions hacienda_canarias gobcan

# Tipos de documentos específicos
python main.py --doc-types Formularios Guías
```

### Uso Programático

```python
from main import CanariasPYMEScraper

# Crear instancia del scraper
scraper = CanariasPYMEScraper()

# Ejecutar scraping completo
scraper.run_scraping()

# Scraping selectivo
scraper.run_scraping(
    institutions=['hacienda_canarias', 'seguridad_social'],
    doc_types=['Formularios']
)
```

### Ejemplos Avanzados

```python
from config.settings import ScrapingConfig
from institution_scrapers.scraper_factory import ScraperFactory

# Configuración personalizada
config = ScrapingConfig('mi_config.json')

# Crear scraper específico
scraper = ScraperFactory.create_scraper(
    'hacienda_canarias', 
    config.TARGET_SOURCES['hacienda_canarias'],
    config
)

# Scrapear documentos
documents = scraper.scrape_documents(['Modelos', 'Impuestos'])
```

## Fuentes de Datos

### Instituciones Configuradas

- **Hacienda Canarias**: Modelos, impuestos, autónomos, sociedades
- **Gobierno de Canarias**: Economía, hacienda, empleo, industria  
- **Cabildos**: Tenerife, Gran Canaria, Lanzarote (extensible)
- **Ayuntamientos**: Santa Cruz, Las Palmas (extensible)
- **Seguridad Social**: Autónomos, empresas, cotización

### Categorías de Documentos

- **Fiscal**: Impuestos, IGIC, IRPF, modelos tributarios
- **Laboral**: Contratos, nóminas, Seguridad Social, autónomos
- **Municipal**: Licencias, tasas, ordenanzas, trámites locales
- **Autonómico**: Subvenciones, ayudas, programas de desarrollo

## Formato de Salida

### Estructura de Metadatos

```json
{
    "document_id": "hash_único_md5",
    "title": "Nombre del documento", 
    "institution": "hacienda_canarias",
    "document_type": "Formulario",
    "category": "fiscal",
    "download_url": "https://...",
    "local_path": "fiscal/hash_único.pdf",
    "metadata": {
        "publication_date": "2024-01-15",
        "last_updated": "2024-03-20T10:30:00",
        "file_type": ".pdf"
    }
}
```

### Archivos Generados

- `metadata.jsonl`: Un documento por línea en formato JSON
- `summary.json`: Resumen estadístico de la ejecución
- Documentos organizados en subdirectorios por categoría

## Monitorización y Logs

### Niveles de Log Disponibles

- **DEBUG**: Información detallada para desarrollo
- **INFO**: Progreso general del scraping
- **WARNING**: Advertencias no críticas
- **ERROR**: Errores que no detienen la ejecución
- **CRITICAL**: Errores graves que detienen el proceso

### Ubicación de Logs

```
logs/
├── scraper_20240320.log    # Log completo del día
└── scraper_latest.log      # Enlace simbólico al último log
```

## Desarrollo y Extensión

### Añadir Nueva Institución

1. **Crear scraper específico**:

```python
# institution_scrapers/mi_nueva_institucion.py
from .base_scraper import BaseScraper

class MiNuevaInstitucionScraper(BaseScraper):
    def scrape_documents(self, doc_types=None):
        # Implementar lógica específica
        pass
    
    def _get_document_links(self, soup, base_url):
        # Implementar extracción de enlaces
        pass
```

2. **Registrar en factory**:

```python
# institution_scrapers/scraper_factory.py
SCRAPER_CLASSES = {
    # ... existing scrapers
    'MiNuevaInstitucionScraper': MiNuevaInstitucionScraper,
}
```

3. **Añadir configuración**:

```python
# config/settings.py
TARGET_SOURCES = {
    # ... existing sources
    "mi_nueva_institucion": {
        "base_url": "https://mi-institucion.com/",
        "areas": ["area1", "area2"],
        "scraper_class": "MiNuevaInstitucionScraper"
    }
}
```

### Personalizar Categorizador

```python
# utils/document_categorizer.py
class DocumentCategorizer:
    def __init__(self):
        # Añadir nuevas categorías
        self.category_keywords["mi_categoria"] = [
            "palabra1", "palabra2", "palabra3"
        ]
```

## Consideraciones Legales y Éticas

### Buenas Prácticas Implementadas

- **Respeto a robots.txt**: Verificación automática
- **Delays entre requests**: Configurables por institución
- **Rate limiting**: Evita sobrecargar servidores
- **User-Agent rotation**: Comportamiento similar a navegador real
- **Manejo de errores**: Reintentos inteligentes con backoff

### Recomendaciones de Uso

- Ejecutar durante horarios de baja actividad
- Monitorizar logs para detectar bloqueos
- Respetar términos de uso de cada sitio web
- Usar únicamente para fines legítimos y educativos

## Solución de Problemas

### Problemas Comunes

**Error de conexión**:
```bash
# Verificar conectividad
python -c "import requests; print(requests.get('https://httpbin.org/ip').json())"
```

**Bloqueo por User-Agent**:
```python
# Verificar rotación de User-Agent en logs
grep "User-Agent" logs/scraper_*.log
```

**Documentos no descargados**:
```python
# Verificar permisos de escritura
import os
print(os.access('./documents', os.W_OK))
```

### Debugging Avanzado

```bash
# Ejecutar en modo debug con salida detallada
python main.py --verbose --institutions hacienda_canarias 2>&1 | tee debug.log

# Analizar metadatos generados
python -c "
import json
with open('documents/metadata.jsonl', 'r') as f:
    for line in f:
        doc = json.loads(line)
        print(f'{doc[\"category\"]}: {doc[\"title\"][:50]}...')
"
```

## Métricas y Estadísticas

### Análisis de Resultados

```python
import json
from collections import Counter

# Cargar summary
with open('documents/summary.json', 'r') as f:
    summary = json.load(f)

print(f"Total documentos: {summary['total_documents']}")
print("Por categoría:", summary['categories'])
print("Por institución:", summary['institutions'])
```

### Monitorización Continua

```bash
# Ver progreso en tiempo real
tail -f logs/scraper_$(date +%Y%m%d).log

# Estadísticas rápidas
wc -l documents/metadata.jsonl
ls -la documents/*/
```

## Contribuciones

### Cómo Contribuir

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Añadir nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### Áreas de Mejora

- [ ] Añadir soporte para más instituciones
- [ ] Implementar interfaz web de administración
- [ ] Mejorar algoritmo de categorización con ML
- [ ] Añadir notificaciones por email/Slack
- [ ] Implementar programación de tareas (cron)

## Soporte

### Recursos de Ayuda

- **Documentación**: Este README
- **Issues**: GitHub Issues (crear según repositorio)
- **Email**: soporte@ejemplo.com (configurar según necesidad)

### FAQ

**P: ¿Cómo añado un proxy?**
R: Modifica `_make_request()` en `BaseScraper` añadiendo parámetro `proxies`.

**P: ¿El sistema funciona con JavaScript?**
R: No, solo contenido HTML estático. Para JS usar Selenium o Playwright.

**P: ¿Puedo programar ejecuciones automáticas?**
R: Sí, usando cron (Linux/Mac) o Task Scheduler (Windows).

## Licencia

MIT License - Ver archivo LICENSE para detalles completos.

## Changelog

### v1.0.0 (2024-03-20)
- Lanzamiento inicial
- Soporte para 7 instituciones canarias
- Sistema de categorización automática
- Arquitectura modular completa

---

# Dockerfile - Contenedor Docker (opcional)
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p documents logs

# Configurar usuario no-root
RUN useradd -m scraper && chown -R scraper:scraper /app
USER scraper

# Comando por defecto
CMD ["python", "main.py", "--verbose"]