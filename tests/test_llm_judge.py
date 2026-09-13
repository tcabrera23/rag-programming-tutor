"""
Tests con LLM-as-a-Judge para evaluar la calidad de las respuestas del agente.

Este módulo usa un LLM como juez para evaluar:
1. Calidad técnica de la respuesta
2. Pertinencia al paradigma correcto
3. Uso correcto de conceptos
4. Claridad de la explicación
"""

import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.domain.agents import get_agent_config
from app.infra.rag import get_rag_instance
import json


class LLMJudge:
    """
    Clase para evaluar respuestas usando un LLM como juez.
    """
    
    def __init__(self, api_key: str):
        """Inicializa el LLM juez."""
        self.judge = ChatOpenAI(
            model="openai/gpt-4o-mini",  # Modelo rápido y económico para evaluar
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            temperature=0.1  # Baja temperatura para evaluaciones consistentes
        )
    
    def evaluate_response(
        self,
        question: str,
        agent_response: str,
        expected_paradigm: str,
        rag_context: str = None
    ) -> dict:
        """
        Evalúa una respuesta del agente.
        
        Args:
            question: Pregunta del usuario
            agent_response: Respuesta del agente
            expected_paradigm: Paradigma esperado (Wollok, Haskell, Prolog)
            rag_context: Contexto recuperado del RAG (opcional)
        
        Returns:
            Dict con scores y análisis
        """
        
        evaluation_prompt = f"""Eres un evaluador experto de respuestas educativas sobre paradigmas de programación.

Tu tarea es evaluar la siguiente respuesta de un agente tutor y asignar puntuaciones de 0 a 10.

**PREGUNTA DEL USUARIO:**
{question}

**PARADIGMA ESPERADO:**
{expected_paradigm} (Orientado a Objetos si es Wollok, Funcional si es Haskell, Lógico si es Prolog)

**RESPUESTA DEL AGENTE:**
{agent_response}

{"**CONTEXTO RAG DISPONIBLE:**" if rag_context else ""}
{rag_context if rag_context else ""}

**CRITERIOS DE EVALUACIÓN:**

1. **Relevancia al Paradigma** (0-10): 
   - ¿La respuesta es específica del paradigma {expected_paradigm}?
   - ¿Menciona conceptos correctos del paradigma?
   
2. **Corrección Técnica** (0-10):
   - ¿La información es técnicamente correcta?
   - ¿Los ejemplos de código son válidos?
   
3. **Claridad y Pedagogía** (0-10):
   - ¿La explicación es clara y comprensible?
   - ¿Es útil para un estudiante?
   
4. **Completitud** (0-10):
   - ¿Responde completamente la pregunta?
   - ¿Faltan aspectos importantes?

5. **Uso del Contexto RAG** (0-10):
   - ¿Usa apropiadamente la información del contexto?
   - ¿Se fundamenta en teoría recuperada?

**FORMATO DE RESPUESTA:**

Responde ÚNICAMENTE con un objeto JSON válido (sin markdown, sin texto adicional):

{{
  "relevancia_paradigma": <score 0-10>,
  "correccion_tecnica": <score 0-10>,
  "claridad_pedagogia": <score 0-10>,
  "completitud": <score 0-10>,
  "uso_contexto_rag": <score 0-10>,
  "score_total": <promedio de los 5 scores>,
  "pasa_calidad": <true si score_total >= 7, false si no>,
  "paradigma_detectado": "<paradigma detectado en la respuesta>",
  "paradigma_correcto": <true si coincide con {expected_paradigm}, false si no>,
  "analisis": "<breve análisis de 1-2 líneas>",
  "problemas_encontrados": ["<lista de problemas, si los hay>"]
}}"""

        # Invocar al juez
        response = self.judge.invoke([
            SystemMessage(content="Eres un evaluador objetivo y estricto. Responde solo con JSON válido."),
            HumanMessage(content=evaluation_prompt)
        ])
        
        # Parsear respuesta JSON
        try:
            # Limpiar respuesta (por si hay markdown)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            evaluation = json.loads(content)
            return evaluation
        except json.JSONDecodeError as e:
            # Si falla el parsing, retornar evaluación de error
            return {
                "error": f"Error al parsear evaluación: {e}",
                "raw_response": response.content,
                "pasa_calidad": False,
                "score_total": 0
            }


@pytest.fixture
def llm_judge(openrouter_api_key):
    """Fixture para crear instancia del LLM juez."""
    return LLMJudge(openrouter_api_key)


class TestWollokResponseQuality:
    """Tests de calidad para respuestas del agente Wollok."""
    
    def test_wollok_basic_question(self, llm_judge, openrouter_api_key, database_url):
        """Test: Evaluar respuesta sobre concepto básico de Wollok."""
        question = "¿Qué es un objeto en Wollok?"
        
        # 1. Obtener configuración y contexto
        agent_config = get_agent_config("Wollok")
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=question,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        rag_context = rag.format_results(results)
        
        # 2. Generar respuesta del agente
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            temperature=0.5
        )
        
        messages = [
            SystemMessage(content=agent_config["system_prompt"]),
            HumanMessage(content=f"{question}\n\nContexto:\n{rag_context}")
        ]
        
        response = llm.invoke(messages)
        agent_response = response.content
        
        # 3. Evaluar con el juez
        evaluation = llm_judge.evaluate_response(
            question=question,
            agent_response=agent_response,
            expected_paradigm="Wollok",
            rag_context=rag_context
        )
        
        # 4. Assertions
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {question}")
        print(f"RESPUESTA: {agent_response[:200]}...")
        print(f"\nEVALUACIÓN:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        assert "error" not in evaluation, f"Error en evaluación: {evaluation.get('error')}"
        assert evaluation["score_total"] >= 6.0, f"Score muy bajo: {evaluation['score_total']}"
        assert evaluation["paradigma_correcto"] is True, f"Paradigma incorrecto detectado: {evaluation.get('paradigma_detectado')}"
    
    def test_wollok_code_question(self, llm_judge, openrouter_api_key, database_url):
        """Test: Evaluar respuesta con código Wollok."""
        question = "Dame un ejemplo de clase en Wollok con atributos y métodos"
        
        agent_config = get_agent_config("Wollok")
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=question,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        rag_context = rag.format_results(results)
        
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            temperature=0.5
        )
        
        messages = [
            SystemMessage(content=agent_config["system_prompt"]),
            HumanMessage(content=f"{question}\n\nContexto:\n{rag_context}")
        ]
        
        response = llm.invoke(messages)
        agent_response = response.content
        
        evaluation = llm_judge.evaluate_response(
            question=question,
            agent_response=agent_response,
            expected_paradigm="Wollok",
            rag_context=rag_context
        )
        
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {question}")
        print(f"RESPUESTA:\n{agent_response}")
        print(f"\nEVALUACIÓN:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        assert "error" not in evaluation
        assert evaluation["score_total"] >= 6.0
        assert evaluation["paradigma_correcto"] is True


class TestHaskellResponseQuality:
    """Tests de calidad para respuestas del agente Haskell."""
    
    def test_haskell_basic_question(self, llm_judge, openrouter_api_key, database_url):
        """Test: Evaluar respuesta sobre concepto básico de Haskell."""
        question = "¿Qué son las funciones de orden superior en Haskell?"
        
        agent_config = get_agent_config("Haskell")
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=question,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        rag_context = rag.format_results(results)
        
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            temperature=0.5
        )
        
        messages = [
            SystemMessage(content=agent_config["system_prompt"]),
            HumanMessage(content=f"{question}\n\nContexto:\n{rag_context}")
        ]
        
        response = llm.invoke(messages)
        agent_response = response.content
        
        evaluation = llm_judge.evaluate_response(
            question=question,
            agent_response=agent_response,
            expected_paradigm="Haskell",
            rag_context=rag_context
        )
        
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {question}")
        print(f"RESPUESTA: {agent_response[:200]}...")
        print(f"\nEVALUACIÓN:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        assert "error" not in evaluation
        assert evaluation["score_total"] >= 6.0
        assert evaluation["paradigma_correcto"] is True


class TestPrologResponseQuality:
    """Tests de calidad para respuestas del agente Prolog."""
    
    def test_prolog_basic_question(self, llm_judge, openrouter_api_key, database_url):
        """Test: Evaluar respuesta sobre concepto básico de Prolog."""
        question = "¿Qué es la unificación en Prolog?"
        
        agent_config = get_agent_config("Prolog")
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=question,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        rag_context = rag.format_results(results)
        
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            temperature=0.5
        )
        
        messages = [
            SystemMessage(content=agent_config["system_prompt"]),
            HumanMessage(content=f"{question}\n\nContexto:\n{rag_context}")
        ]
        
        response = llm.invoke(messages)
        agent_response = response.content
        
        evaluation = llm_judge.evaluate_response(
            question=question,
            agent_response=agent_response,
            expected_paradigm="Prolog",
            rag_context=rag_context
        )
        
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {question}")
        print(f"RESPUESTA: {agent_response[:200]}...")
        print(f"\nEVALUACIÓN:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        assert "error" not in evaluation
        # Score puede ser más bajo si el seed de Prolog no cubre el tema
        assert evaluation["score_total"] >= 4.0, f"Score muy bajo: {evaluation['score_total']}"
        assert evaluation["paradigma_correcto"] is True


class TestCrossParadigmDetection:
    """Tests para detectar mezcla incorrecta de paradigmas."""
    
    def test_detect_wrong_paradigm(self, llm_judge, openrouter_api_key):
        """Test: Detectar cuando se responde con paradigma incorrecto."""
        question = "¿Qué es un objeto en Wollok?"
        
        # Simular respuesta incorrecta (responder con Haskell para pregunta de Wollok)
        wrong_response = """
        En Haskell, no tenemos objetos como en la programación orientada a objetos.
        En su lugar, trabajamos con funciones puras y tipos de datos algebraicos.
        Por ejemplo, usamos data types y pattern matching.
        """
        
        evaluation = llm_judge.evaluate_response(
            question=question,
            agent_response=wrong_response,
            expected_paradigm="Wollok"
        )
        
        print(f"\n{'='*60}")
        print(f"TEST: Detección de paradigma incorrecto")
        print(f"PREGUNTA: {question}")
        print(f"RESPUESTA INCORRECTA: {wrong_response}")
        print(f"\nEVALUACIÓN:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        # Este test debería fallar la evaluación
        assert evaluation["paradigma_correcto"] is False, "Debería detectar paradigma incorrecto"
        assert evaluation["pasa_calidad"] is False, "No debería pasar calidad"

