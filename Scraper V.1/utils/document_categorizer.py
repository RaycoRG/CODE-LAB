import re
from typing import Dict, List
import logging


class DocumentCategorizer:
    """Categorizador automático de documentos usando keywords"""
    
    def __init__(self):
        self.logger = logging.getLogger("canarias_scraper.categorizer")
        
        # Palabras clave para cada categoría
        self.category_keywords = {
            "fiscal": [
                "impuesto", "igic", "irpf", "iva", "tributario", "fiscal", 
                "hacienda", "modelo", "declaracion", "liquidacion", "aeat",
                "recargo", "bonificacion", "exencion", "contribucion"
            ],
            "laboral": [
                "trabajo", "empleo", "contrato", "nomina", "seguridad social",
                "autonomo", "cotizacion", "prestacion", "desempleo", "sepe",
                "convenio", "laboral", "trabajador", "empresa", "mutua"
            ],
            "municipal": [
                "licencia", "municipal", "ayuntamiento", "ordenanza", "tasa",
                "canon", "ocupacion", "via publica", "actividad", "apertura",
                "obras", "urbanismo", "cabildo", "insular"
            ],
            "autonomico": [
                "canarias", "gobierno", "consejeria", "decreto", "ley",
                "subvencion", "ayuda", "fondo", "plan", "programa",
                "desarrollo", "competitividad", "innovacion"
            ]
        }
    
    def categorize(self, title: str, content: str = "") -> str:
        """Categoriza un documento basado en su título y contenido"""
        text = f"{title} {content}".lower()
        
        # Calcular puntuaciones por categoría
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[category] = score
        
        # Determinar categoría con mayor puntuación
        if not scores or max(scores.values()) == 0:
            return "general"
        
        best_category = max(scores, key=scores.get)
        
        self.logger.debug(f"📊 Categorización: '{title[:50]}...' -> {best_category} (score: {scores[best_category]})")
        
        return best_category