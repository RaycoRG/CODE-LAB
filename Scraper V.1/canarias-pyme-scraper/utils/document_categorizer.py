"""
Categorizador automático de documentos mejorado
Versión optimizada con mejor algoritmo de clasificación
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class DocumentCategorizer:
    """Categorizador inteligente de documentos usando análisis de keywords y contexto"""
    
    def __init__(self):
        self.logger = logging.getLogger("canarias_scraper.categorizer")
        
        # Diccionario extendido de palabras clave por categoría
        self.category_keywords = {
            "fiscal": {
                # Pesos: 3=muy relevante, 2=relevante, 1=algo relevante
                3: ["impuesto", "igic", "irpf", "iva", "tributario", "fiscal", "hacienda", 
                    "modelo", "declaracion", "liquidacion", "aeat", "agencia tributaria"],
                2: ["recargo", "bonificacion", "exencion", "contribucion", "gravamen",
                    "cuota", "base imponible", "deduccion", "retencion"],
                1: ["canon", "tasa municipal", "precio publico", "tributo", "ingreso"]
            },
            "laboral": {
                3: ["trabajo", "empleo", "contrato", "nomina", "seguridad social",
                    "autonomo", "cotizacion", "afiliacion", "sepe"],
                2: ["prestacion", "desempleo", "convenio", "laboral", "trabajador", 
                    "mutua", "accidente laboral", "incapacidad", "jubilacion"],
                1: ["formacion", "cualificacion", "competencia profesional", "riesgo laboral"]
            },
            "municipal": {
                3: ["licencia", "municipal", "ayuntamiento", "ordenanza", "actividad",
                    "apertura", "obras", "urbanismo", "cabildo"],
                2: ["tasa", "canon", "ocupacion via publica", "terraza", "valla publicitaria",
                    "mercadillo", "feria", "espectaculo"],
                1: ["registro", "censo", "padron", "empadronamiento", "certificado municipal"]
            },
            "autonomico": {
                3: ["canarias", "gobierno", "consejeria", "decreto", "ley canaria",
                    "subvencion", "ayuda", "programa", "plan"],
                2: ["fondo", "desarrollo", "competitividad", "innovacion", "i+d+i",
                    "internacionalizacion", "exportacion", "zona especial canaria"],
                1: ["turismo", "agricultura", "pesca", "energia renovable", "medio ambiente"]
            },
            "comercial": {
                3: ["comercio", "camara comercio", "exportacion", "importacion",
                    "comercio exterior", "arancel", "mercado"],
                2: ["certificado origen", "documento comercial", "factura comercial",
                    "credito documentario", "incoterms"],
                1: ["feria comercial", "mision comercial", "promocion", "marketing"]
            },
            "societario": {
                3: ["sociedad", "empresa", "constitucion", "estatutos", "capital social",
                    "registro mercantil", "administrador"],
                2: ["fusion", "escision", "transformacion", "disolucion", "concurso",
                    "junta general", "consejo administracion"],
                1: ["marca", "patente", "propiedad industrial", "denominacion social"]
            }
        }
        
        # Patrones específicos por categoría
        self.category_patterns = {
            "fiscal": [
                r"modelo\s+\d+", r"igic\s+general", r"irpf\s+\d+",
                r"iva\s+trimestral", r"declaracion\s+anual"
            ],
            "laboral": [
                r"contrato\s+\w+", r"nomina\s+\d+", r"convenio\s+colectivo",
                r"seguridad\s+social", r"cotizacion\s+\d+"
            ],
            "municipal": [
                r"licencia\s+\w+", r"ordenanza\s+\d+", r"tasa\s+municipal",
                r"obra\s+mayor", r"actividad\s+comercial"
            ],
            "autonomico": [
                r"decreto\s+\d+", r"ley\s+\d+/\d+", r"subvencion\s+\d+",
                r"plan\s+\w+", r"programa\s+\w+"
            ]
        }
        
        # Instituciones y sus categorías típicas
        self.institution_categories = {
            "hacienda": ["fiscal"],
            "seguridad_social": ["laboral"],
            "sepe": ["laboral"],
            "ayuntamiento": ["municipal"],
            "ayto": ["municipal"],
            "cabildo": ["municipal", "autonomico"],
            "gobcan": ["autonomico"],
            "gobierno": ["autonomico"],
            "camara": ["comercial", "societario"]
        }
    
    def categorize(self, title: str, content: str = "", 
                  institution: str = "", url: str = "") -> str:
        """
        Categoriza un documento usando análisis multicriterio
        
        Args:
            title: Título del documento
            content: Contenido/descripción del documento
            institution: Institución de origen
            url: URL del documento
            
        Returns:
            Categoría asignada
        """
        # Preparar texto para análisis
        full_text = f"{title} {content}".lower().strip()
        
        if not full_text or len(full_text) < 3:
            return "general"
        
        # Calcular puntuaciones por categoría
        category_scores = self._calculate_category_scores(
            full_text, institution, url
        )
        
        # Aplicar heurísticas adicionales
        category_scores = self._apply_heuristics(
            category_scores, title, content, institution
        )
        
        # Determinar mejor categoría
        best_category = self._select_best_category(category_scores)
        
        # Log del resultado
        self._log_categorization_result(title, best_category, category_scores)
        
        return best_category
    
    def _calculate_category_scores(self, text: str, institution: str = "", 
                                 url: str = "") -> Dict[str, float]:
        """Calcula puntuaciones base por categoría"""
        scores = defaultdict(float)
        
        # 1. Puntuación por keywords con pesos
        for category, weight_groups in self.category_keywords.items():
            for weight, keywords in weight_groups.items():
                for keyword in keywords:
                    # Contar ocurrencias de la keyword
                    occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
                    scores[category] += occurrences * weight
        
        # 2. Puntuación por patrones regex
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                scores[category] += matches * 2  # Peso alto para patrones específicos
        
        # 3. Bonus por institución
        if institution:
            inst_lower = institution.lower()
            for inst_keyword, categories in self.institution_categories.items():
                if inst_keyword in inst_lower:
                    for category in categories:
                        scores[category] += 1.5
        
        # 4. Bonus por URL
        if url:
            url_lower = url.lower()
            for category in self.category_keywords.keys():
                if category in url_lower:
                    scores[category] += 1
        
        return dict(scores)
    
    def _apply_heuristics(self, scores: Dict[str, float], title: str, 
                         content: str, institution: str) -> Dict[str, float]:
        """Aplica reglas heurísticas para mejorar la categorización"""
        title_lower = title.lower()
        
        # Heurística 1: Documentos con números modelo son típicamente fiscales
        if re.search(r'modelo\s+\d+', title_lower):
            scores['fiscal'] += 3
        
        # Heurística 2: Formularios de empleo
        if any(term in title_lower for term in ['contrato', 'empleo', 'trabajo']):
            scores['laboral'] += 2
        
        # Heurística 3: Licencias y permisos son municipales
        if any(term in title_lower for term in ['licencia', 'permiso', 'autorizacion']):
            if 'municipal' in title_lower or 'ayuntamiento' in institution.lower():
                scores['municipal'] += 2
        
        # Heurística 4: Subvenciones son autonómicas
        if any(term in title_lower for term in ['subvencion', 'ayuda', 'beca']):
            scores['autonomico'] += 2
        
        # Heurística 5: Documentos comerciales/empresariales
        commercial_terms = ['exportacion', 'comercio', 'camara', 'empresa', 'sociedad']
        if any(term in title_lower for term in commercial_terms):
            scores['comercial'] += 1.5
            scores['societario'] += 1.5
        
        return scores
    
    def _select_best_category(self, scores: Dict[str, float]) -> str:
        """Selecciona la mejor categoría basada en las puntuaciones"""
        if not scores or max(scores.values()) == 0:
            return "general"
        
        # Encontrar categoría(s) con máxima puntuación
        max_score = max(scores.values())
        top_categories = [cat for cat, score in scores.items() if score == max_score]
        
        # Si hay empate, aplicar criterios de desempate
        if len(top_categories) > 1:
            return self._resolve_tie(top_categories, scores)
        
        return top_categories[0]
    
    def _resolve_tie(self, tied_categories: List[str], 
                    scores: Dict[str, float]) -> str:
        """Resuelve empates entre categorías"""
        # Prioridades de categorías (menor número = mayor prioridad)
        category_priorities = {
            "fiscal": 1,
            "laboral": 2, 
            "municipal": 3,
            "autonomico": 4,
            "comercial": 5,
            "societario": 6,
            "general": 7
        }
        
        # Seleccionar categoría con mayor prioridad
        best_category = min(tied_categories, 
                          key=lambda x: category_priorities.get(x, 999))
        
        return best_category
    
    def _log_categorization_result(self, title: str, category: str, 
                                  scores: Dict[str, float]):
        """Log del resultado de categorización"""
        title_short = title[:50] + "..." if len(title) > 50 else title
        
        if scores:
            top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            scores_str = ", ".join([f"{cat}:{score:.1f}" for cat, score in top_scores])
            self.logger.debug(f"Categorizado: '{title_short}' -> {category} ({scores_str})")
        else:
            self.logger.debug(f"Categorizado: '{title_short}' -> {category} (sin puntuación)")
    
    def get_category_suggestions(self, text: str) -> List[Tuple[str, float]]:
        """Obtiene sugerencias de categorías ordenadas por puntuación"""
        scores = self._calculate_category_scores(text.lower())
        
        if not scores:
            return [("general", 0.0)]
        
        # Normalizar puntuaciones
        max_score = max(scores.values())
        normalized_scores = [(cat, score/max_score) for cat, score in scores.items()]
        
        # Ordenar por puntuación descendente
        return sorted(normalized_scores, key=lambda x: x[1], reverse=True)
    
    def add_custom_keywords(self, category: str, keywords: List[str], weight: int = 1):
        """Añade palabras clave personalizadas a una categoría"""
        if category not in self.category_keywords:
            self.category_keywords[category] = {1: [], 2: [], 3: []}
        
        if weight not in self.category_keywords[category]:
            self.category_keywords[category][weight] = []
        
        self.category_keywords[category][weight].extend(keywords)
        
        self.logger.info(f"Añadidas {len(keywords)} keywords a categoría {category} con peso {weight}")
    
    def get_category_stats(self) -> Dict[str, int]:
        """Retorna estadísticas de keywords por categoría"""
        stats = {}
        for category, weight_groups in self.category_keywords.items():
            total_keywords = sum(len(keywords) for keywords in weight_groups.values())
            stats[category] = total_keywords
        
        return stats