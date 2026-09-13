"""
Clasificador de dificultad de consultas para optimizar selección de LLM.
"""

import re
from dataclasses import dataclass
from typing import Dict, Literal, Tuple

QueryType = Literal["theoretical", "coding", "debugging", "conceptual"]
Difficulty = Literal["simple", "medium", "complex"]


@dataclass
class QueryClassification:
    query_type: QueryType
    difficulty: Difficulty
    suggested_model_tier: str
    confidence: float
    reasoning: str


class QueryClassifier:
    THEORETICAL_PATTERNS = [
        r"\b(qu[eé] es|define|explica|concepto|teor[ií]a)\b",
        r"\b(diferencia entre|comparar|ventaja|desventaja)\b",
        r"\b(paradigma|principio|fundamento)\b",
    ]

    CODING_PATTERNS = [
        r"\b(escrib[ie]|implement[ae]|crea|codifica|programa)\b",
        r"\b(funci[oó]n|m[eé]todo|clase|objeto|predicado)\b",
        r"\b(c[oó]digo|soluci[oó]n|ejercicio|problema)\b",
        r"\b(resuelve|resolver|desarrolla|haz que)\b",
    ]

    DEBUGGING_PATTERNS = [
        r"\b(error|falla|bug|problema con|no funciona)\b",
        r"\b(debug|depura|corrige|arregla|fix)\b",
        r"\b(por qu[eé] no|c[oó]mo soluciono)\b",
    ]

    SIMPLE_INDICATORS = [
        r"\b(qu[eé] es|define|ejemplo simple)\b",
        r"^.{1,50}$",
    ]

    COMPLEX_INDICATORS = [
        r"\b(implementar|desarrollar|optimizar|refactorizar)\b",
        r"\b(m[uú]ltiples|varios|diferentes|combinar)\b",
        r"\b(pattern|patr[oó]n|arquitectura|dise[ñn]o)\b",
        r"^.{200,}$",
    ]

    def classify(self, query: str, context: Dict = None) -> QueryClassification:
        query_lower = query.lower()
        query_type, type_confidence = self._determine_query_type(query_lower)
        difficulty, diff_confidence = self._determine_difficulty(query_lower, context)
        model_tier = self._suggest_model_tier(query_type, difficulty)
        overall_confidence = (type_confidence + diff_confidence) / 2
        reasoning = self._build_reasoning(query_type, difficulty, model_tier)
        return QueryClassification(
            query_type=query_type,
            difficulty=difficulty,
            suggested_model_tier=model_tier,
            confidence=overall_confidence,
            reasoning=reasoning,
        )

    def _determine_query_type(self, query: str) -> Tuple[QueryType, float]:
        scores = {
            "theoretical": self._count_pattern_matches(query, self.THEORETICAL_PATTERNS),
            "debugging": self._count_pattern_matches(query, self.DEBUGGING_PATTERNS),
            "coding": self._count_pattern_matches(query, self.CODING_PATTERNS),
        }
        if all(score == 0 for score in scores.values()):
            return "conceptual", 0.5
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5
        return max_type, min(confidence, 1.0)

    def _determine_difficulty(self, query: str, context: Dict = None) -> Tuple[Difficulty, float]:
        simple_score = self._count_pattern_matches(query, self.SIMPLE_INDICATORS)
        complex_score = self._count_pattern_matches(query, self.COMPLEX_INDICATORS)
        has_attachment = context and context.get("has_attachment", False)
        query_length = len(query)
        if has_attachment:
            complex_score += 1
        if query_length < 30:
            simple_score += 1
        elif query_length > 150:
            complex_score += 1
        if simple_score > complex_score:
            return "simple", 0.8
        if complex_score > simple_score * 1.5:
            return "complex", 0.9
        return "medium", 0.7

    def _suggest_model_tier(self, query_type: QueryType, difficulty: Difficulty) -> str:
        tier_matrix = {
            ("theoretical", "simple"): "economy",
            ("theoretical", "medium"): "economy",
            ("theoretical", "complex"): "balanced",
            ("conceptual", "simple"): "economy",
            ("conceptual", "medium"): "balanced",
            ("conceptual", "complex"): "balanced",
            ("coding", "simple"): "balanced",
            ("coding", "medium"): "balanced",
            ("coding", "complex"): "premium",
            ("debugging", "simple"): "balanced",
            ("debugging", "medium"): "balanced",
            ("debugging", "complex"): "premium",
        }
        return tier_matrix.get((query_type, difficulty), "balanced")

    def _count_pattern_matches(self, text: str, patterns: list) -> int:
        count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count

    def _build_reasoning(self, query_type: QueryType, difficulty: Difficulty, tier: str) -> str:
        type_desc = {
            "theoretical": "pregunta teórica",
            "coding": "desarrollo de código",
            "debugging": "depuración/debugging",
            "conceptual": "consulta conceptual",
        }
        diff_desc = {"simple": "simple", "medium": "moderada", "complex": "compleja"}
        tier_desc = {
            "economy": "modelo económico",
            "balanced": "modelo balanceado",
            "premium": "modelo premium",
        }
        return (
            f"Clasificada como {type_desc[query_type]} de dificultad {diff_desc[difficulty]}. "
            f"Sugerido: {tier_desc[tier]}."
        )


_classifier_instance = None


def get_classifier() -> QueryClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = QueryClassifier()
    return _classifier_instance
