# Changelog - ChatPdeP

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y [Semantic Versioning](https://semver.org/lang/es/).

---

## [Unreleased]

### Cambiado

- Backend reorganizado en `app/` (delivery, services, domain, infra). Streamlit y FastAPI usan el mismo turno (`app.services.chat`).
- UI Streamlit en `streamlit_app.py` (no puede coexistir `app.py` con el paquete `app/`).
- Documentación compactada: README + anexos en `docs/` (supabase, security, testing).
- RAG contra Postgres + pgvector local (`DATABASE_URL` + psycopg). Schema y seed de Wollok/Haskell/Prolog en `db/`. Supabase queda opcional solo para métricas.

---

## [2.0.0] - 2026-02-12

### 🎉 Nueva Versión Mayor - Grandes Mejoras

### ✨ Nuevas Características

#### 💻 Soporte para Modelos Locales (Ollama)
- **Agregado** integración completa con Ollama
- **Agregado** contenedor Docker para Ollama con instalación automática de phi4-mini
- **Agregado** soporte para modelos locales: phi4-mini, qwen3-4b, deepseek-coder-6.7b, qwen2.5-coder-7b
- **Agregado** configuración automática de red entre servicios Docker
- **Agregado** persistencia de modelos descargados con volumen Docker
- **Agregado** `docker-compose.cpu.yml` para sistemas sin GPU

#### 🌐 Selector de Proveedor Dinámico
- **Agregado** selector de proveedor en sidebar: Cloud (OpenRouter) vs Local (Ollama)
- **Agregado** configuración dinámica de URL de Ollama
- **Agregado** sugerencias de modelos para instalar con Ollama
- **Agregado** detección automática de disponibilidad de Ollama

#### 🎯 Clasificación Automática de Consultas
- **Agregado** nuevo módulo `utils/query_classifier.py`
- **Agregado** clasificador que analiza:
  - Tipo de consulta (teórica, código, debugging, conceptual)
  - Dificultad (simple, media, compleja)
  - Tier sugerido (economy, balanced, premium)
- **Agregado** switch automático de modelo según clasificación
- **Agregado** optimización de costos con selección inteligente
- **Agregado** toggle para habilitar/deshabilitar auto-clasificación
- **Agregado** notificaciones de clasificación en tiempo real

#### 🤖 Gestor de Modelos Centralizado
- **Agregado** nuevo módulo `utils/model_manager.py`
- **Agregado** clase `ModelManager` para gestión unificada de modelos
- **Agregado** catálogo de modelos predefinidos con metadata (costos, contexto, tier)
- **Agregado** soporte para modelos personalizados del usuario
- **Agregado** métodos para crear LLMs con cualquier proveedor
- **Agregado** persistencia de modelos personalizados en session_state

#### ➕ Modelos Personalizados desde OpenRouter
- **Agregado** interfaz en sidebar para agregar modelos personalizados
- **Agregado** posibilidad de copiar/pegar ID de modelo desde OpenRouter
- **Agregado** configuración de tier para modelos personalizados
- **Agregado** validación de modelos antes de agregar
- **Agregado** listado de modelos personalizados agregados

#### 🔄 Sistema de Fallbacks Inteligente
- **Agregado** método `create_llm_with_fallback()` en ModelManager
- **Agregado** fallback automático a Gemini 2.5 Flash Lite si un modelo falla
- **Agregado** notificaciones específicas según tipo de fallo:
  - Modelo local falla → sugiere usar cloud
  - Modelo cloud falla → usa Gemini automáticamente
- **Agregado** mensajes informativos sobre razón del fallback
- **Agregado** manejo de errores más robusto

#### 📝 Summarización Mejorada
- **Mejorado** detección automática de límite de contexto por modelo
- **Agregado** uso de 80% del contexto del modelo como límite seguro
- **Mejorado** cálculo dinámico basado en `ModelConfig.context_window`
- **Agregado** soporte para modelos personalizados en summarización
- **Mejorado** eficiencia de cálculo de tokens aproximados

### 🔧 Mejoras Técnicas

#### Arquitectura y Código
- **Agregado** separación de responsabilidades con nuevos módulos
- **Mejorado** tipado con `Literal` y `dataclass` en Python
- **Agregado** singletons para managers (`get_model_manager()`, `get_classifier()`)
- **Mejorado** manejo de errores con try-except específicos
- **Agregado** logging y notificaciones más descriptivas

#### Docker y DevOps
- **Mejorado** `docker-compose.yml` con servicio de Ollama
- **Agregado** `docker-compose.cpu.yml` para usuarios sin GPU
- **Agregado** instalación automática de phi4-mini al levantar
- **Agregado** volumen `ollama_models` para persistencia
- **Agregado** configuración de GPU con `deploy.resources` (opcional)
- **Mejorado** networking entre servicios

#### Interfaz de Usuario
- **Mejorado** sidebar con nuevas secciones organizadas
- **Agregado** radio button para selector de proveedor
- **Agregado** expander para sugerencias de modelos Ollama
- **Agregado** expander para agregar modelos personalizados
- **Agregado** toggle para auto-clasificación
- **Agregado** indicadores de tier y costos en selector de modelos
- **Mejorado** información mostrada en área principal (modelo auto/manual)
- **Agregado** notificaciones de clasificación y fallbacks en chat

### 📚 Documentación

- **Agregado** `NEW_VERSION.md` con descripción detallada de v2.0
- **Agregado** `INSTALLATION_GUIDE.md` con guía completa de instalación
- **Agregado** `CHANGELOG.md` (este archivo)
- **Actualizado** `README.md` con nuevas características
- **Actualizado** `.env.example` con nuevas variables (OLLAMA_BASE_URL)
- **Agregado** ejemplos de uso para todas las nuevas características
- **Agregado** sección de troubleshooting en INSTALLATION_GUIDE.md
- **Agregado** comparativa de modelos cloud vs local en NEW_VERSION.md

### 📦 Dependencias

- **Agregado** `ollama==0.4.5` para integración con Ollama
- **Actualizado** `requirements.txt` con formato limpio

### 🐛 Correcciones de Bugs

- **Corregido** referencias a `selected_model` por `selected_model_id`
- **Corregido** uso de modelo en base de datos (ahora guarda `final_model_id`)
- **Corregido** mostrar modelo correcto en área principal cuando auto-clasificar está activo
- **Corregido** encoding de `requirements.txt`

### 🔐 Seguridad

- **Mantenido** uso de `SUPABASE_ANON_KEY` con RLS (no `SERVICE_KEY`)
- **Agregado** validación de API keys antes de crear LLMs
- **Mejorado** manejo de errores sin exponer información sensible

### ⚡ Rendimiento

- **Optimizado** selección de modelo según complejidad de consulta
- **Reducido** costos de tokens en 60-80% con auto-clasificación
- **Agregado** opción de usar modelos locales ($0 en costos)
- **Mejorado** uso de memoria con configuración CPU/GPU en Docker

### 🎨 Estilos y UX

- **Mejorado** organización del sidebar con secciones claras
- **Agregado** iconos para diferentes proveedores (☁️ Cloud, 💻 Local)
- **Agregado** emojis en notificaciones (🎯 clasificación, 🔄 fallback)
- **Mejorado** legibilidad de información de modelos
- **Agregado** indicadores visuales de tier (economy/balanced/premium)

---

## [1.0.0] - 2025-12-XX (Versión Anterior)

### ✨ Características Iniciales

- Chat interactivo con Streamlit
- Tres agentes especializados (Wollok, Haskell, Prolog)
- RAG con Supabase y pgvector
- Soporte para archivos adjuntos (PDF, imágenes)
- Historial persistente con SQLite
- Selección de modelos de OpenRouter
- Ventana de contexto configurable
- Summarización básica de conversaciones
- Testing con LLM-as-a-Judge
- Dockerización básica

---

## Formato del Changelog

Este changelog sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

### Tipos de Cambios

- **Agregado** para nuevas características
- **Cambiado** para cambios en funcionalidad existente
- **Obsoleto** para características que serán removidas
- **Removido** para características eliminadas
- **Corregido** para bugs arreglados
- **Seguridad** para vulnerabilidades

---

**Versión actual:** 2.0.0  
**Última actualización:** 2026-02-12
