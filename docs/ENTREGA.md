# Entrega — TP Final Coding Agent Avanzado

Documento índice de la entrega. Cada sección responde a un entregable del enunciado y
apunta a dónde está la evidencia en el repo.

| Entregable | Dónde |
| --- | --- |
| 1. Código funcionando | `src/coding_agent/` + `cases/football_predictor/` |
| 2. README instalación/config/ejecución | [`README.md`](../README.md) |
| 3. Caso de uso (objetivo + criterio) | §3 de este doc + [`cases/football_predictor/README.md`](../cases/football_predictor/README.md) |
| 4. Arquitectura (agente + subagentes + estado) | §4 de este doc + [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| 5. Documentación de la base RAG | §5 de este doc |
| 6. Evidencia de ≥2 tareas ejecutadas | [`docs/EVIDENCE.md`](EVIDENCE.md) |
| 7. Capturas de observabilidad | Langfuse (traza `coding-agent-task`) — ver §7 |
| 8. Reflexión | §8 de este doc |

---

## 3. Caso de uso

**Proyecto:** `cases/football_predictor/` — un pipeline en Python/pandas que predice un
partido entre dos selecciones.

**Objetivo concreto:** dado un cruce (ej. Argentina vs Francia), producir una predicción
**probabilística** reproducible (gana A / empate / gana B) y **evaluarla** con métricas de
calibración sobre datos históricos, sin data leakage.

**Por qué sirve para el agente:** es un repo real que el agente puede explorar, correr,
evaluar, mejorar y explicar. Las tareas de prueba (memoria, RAG, cambio de estrategia) se
ejecutan sobre este workspace.

**Criterio de "cumplido" (verificable):**

1. El pipeline corre de punta a punta sobre el **dataset real** (martj42, 49.495 partidos
   jugados 1872→2026) sin data leakage — cada feature usa solo el historial previo al partido.
2. El modelo principal (Poisson) **supera al baseline (Elo)** en las métricas de calibración.

**Resultado (test set = últimos 300 partidos, menor es mejor):**

| Métrica | Elo baseline | Poisson v2 |
| --- | --- | --- |
| Brier | 0.5479 | **0.5221** |
| Log loss | 0.9264 | **0.8903** |
| RPS | 0.1770 | **0.1642** |

Criterio cumplido. El detalle del modelo (v1 perdía, se diagnosticó y rediseñó a v2 con
supremacía Elo log-lineal + localía, eligiendo parámetros en validación y confirmando en un
test set no tocado) está en [`cases/football_predictor/README.md`](../cases/football_predictor/README.md).

---

## 4. Arquitectura (resumen)

Detalle completo en [`docs/ARCHITECTURE.md`](ARCHITECTURE.md). En una frase:

```
Usuario → main.py → CodingAgentOrchestrator → TaskState (estado compartido)
        → MainAgent coordina Explorer/Researcher → Brief compartido
        → Harness (loop LLM ↔ tools, con permisos + loop guard)
        → TaskState + ProjectMemory + TraceRecorder
```

- **Agente principal (`CodingAgentOrchestrator`):** recibe la tarea, mantiene el estado,
  coordina subagentes, arma el brief y ejecuta el harness.
- **Subagentes:** `Explorer` (estructura/archivos del repo), `Researcher` (fuentes locales,
  memoria, RAG/web), y el pipeline `Planner → Coder → Test → Reviewer`. Cada uno tiene una
  responsabilidad acotada y aporta evidencia/criterio al brief; no todos necesitan las
  mismas tools.
- **Estado compartido (`TaskState`):** pedido, progreso, resultados de subagentes, fuentes,
  tool calls, archivos modificados, observaciones, errores, iteraciones y respuesta final.
  Se serializa a `runs/task_states/<id>.json`.
- **Harness:** llama al LLM, valida permisos **antes** de cada tool call, pide aprobación
  cuando corresponde, ejecuta tools y detecta repeticiones sin avance (`loop_guard.py`).

---

## 5. Documentación de la base RAG

RAG mínimo, sin frameworks externos. Pipeline: `chunker → embeddings → vector_store → retriever`,
expuesto como la tool `rag_search`.

- **Fuentes** (`rag_docs/`, 5 documentos técnicos del ecosistema del caso):
  `pandas.md`, `pytest.md`, `data_leakage.md`, `elo.md`, `poisson.md`.
- **Chunking** (`rag/chunker.py`): por caracteres con solapamiento, `chunk_size=800`,
  `overlap=150`. Los 5 docs generan **8 chunks**.
- **Embeddings** (`rag/embeddings.py`): API de OpenAI, modelo `text-embedding-3-small`.
- **Almacenamiento** (`rag/vector_store.py`): índice JSON local en
  `storage/vector_store/index.json` (source, chunk_id, texto, embedding).
- **Recuperación** (`rag/retriever.py`): similitud **coseno**, `top_k=3` por defecto. La tool
  devuelve cada resultado con `Fuente`, `Chunk`, `Score` y `Contenido`, para que las
  afirmaciones sean verificables y se distinga la fuente (RAG vs repo vs memoria vs web).
- **Política:** el `SYSTEM_PROMPT` obliga a consultar `rag_search` primero y usar `web_search`
  solo como fallback. Ingesta: `PYTHONPATH=src python -m coding_agent.rag.ingest`.

---

## 7. Observabilidad

Cada corrida se registra en `TraceRecorder`: prompts, modelo, llamadas al LLM, tools, fuentes
RAG/web, iteraciones, errores, latencia, tokens, costo estimado y resultado final. Guarda
**trazas locales** en `runs/traces/<id>.json` (independiente de servicios externos) y exporta
a **Langfuse**.

Config del `.env` (SDK v3 lee `LANGFUSE_HOST`, **no** `LANGFUSE_BASE_URL`; región del proyecto: US):

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

Para la captura (entregable 7): dashboard de Langfuse → filtrar por nombre `coding-agent-task`
→ abrir una traza (muestra el árbol de spans: brief, iteraciones LLM, tool calls con sus
resultados, tokens, latencia y costo). Los `task_id` de cada corrida están en [`docs/EVIDENCE.md`](EVIDENCE.md).

---

## 8. Reflexión

### Qué funcionó bien

- **RAG con fuentes visibles.** `rag_search` devuelve el chunk con su `Fuente` y `Score`, lo
  que hace verificable cada afirmación y permite distinguir RAG / repo / memoria / web.
- **Memoria persistente útil.** En la tarea de memoria el agente recuperó y **citó** una
  decisión y un comando guardados, aclarando que venían de la memoria del proyecto.
- **Políticas antes de ejecutar.** Cada tool call se valida contra `agent.config.yaml` antes
  de correr; da una red de seguridad real (paths y comandos denegados, aprobaciones).
- **Observabilidad que no depende de terceros.** Las trazas locales se generan siempre, aun
  cuando Langfuse falló; eso permitió depurar sin el dashboard.
- **Mejora medible del caso.** El modelo pasó de perder contra el baseline a superarlo, con
  una metodología honesta (validación separada del test).

### Qué falló / aristas ásperas

- **El Poisson v1 perdía contra el Elo simple** sobre datos reales: estaba sobre-parametrizado
  (apilaba factores clampeados) y desaprovechaba el Elo. Se diagnosticó y rediseñó (v2).
- **Config de Langfuse frágil.** El `.env` usaba `LANGFUSE_BASE_URL` (el SDK v3 lee
  `LANGFUSE_HOST`) y tenía una comilla sin cerrar que metía un `\n` en el host y rompía el
  DNS. El error visible (`timeout`/`401`) no señalaba la causa real.
- **Manejo de excepciones del trace.** En una corrida la tarea de estrategia terminó `blocked`
  con `"generator didn't stop after throw()"`: una excepción dentro de `trace.trace_task()`
  no se maneja limpio.
- **Loop guard sin corte duro + costo O(n²).** El loop guard avisa pero no frena; una corrida
  llegó a 32 iteraciones. Y `evaluate` recomputaba el Elo por partido (O(n²)), inviable en
  49k partidos hasta agregar `--max-eval`.

### Cuándo se detectaron loops o falta de evidencia

- **Loop:** en la tarea "arreglá el módulo de pagos", el agente repitió `list_files` sobre una
  ruta inexistente; el **loop guard lo detectó** ("repeated action... change strategy or ask
  for help") y el agente dejó de repetir.
- **Falta de evidencia:** el módulo `payments.py` no existe; el agente lo **reconoció y pidió
  ayuda** en lugar de inventar un fix ("no tengo suficientes evidencias... ¿me confirmás la
  ruta o el error?").

### Qué mejoraríamos

1. **Tope duro de iteraciones por turno** (no solo el nudge del loop guard) y manejo de
   excepciones limpio en `trace_task` (arreglar el `generator didn't stop`).
2. **Evaluación incremental O(n)** (un solo forward pass computando Elo/stats) para poder
   evaluar miles de partidos en segundos.
3. **Modelo:** correlación de goles (Dixon-Coles) y ranking FIFA / valor de plantel como
   features adicionales.
4. **Contexto:** resumen de historial con LLM, y subagentes con tools propias (hoy aportan
   criterio, no ejecución autónoma).
5. **Extra opcional:** sistema de plugins de tools con autodescubrimiento.
