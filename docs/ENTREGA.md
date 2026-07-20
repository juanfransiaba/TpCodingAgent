# Entrega — TP Final Coding Agent Avanzado

Documento índice de la entrega. Cada sección responde a un entregable del enunciado y
apunta a dónde está la evidencia en el repo.

| Entregable | Dónde |
| --- | --- |
| 1. Código funcionando | `src/coding_agent/` + repo objetivo externo `choppedapp_copia` |
| 2. README instalación/config/ejecución | [`README.md`](../README.md) |
| 3. Caso de uso (objetivo + criterio) | §3 de este doc + [`docs/CASO_DE_USO.md`](CASO_DE_USO.md) |
| 4. Arquitectura (agente + subagentes + estado) | §4 de este doc + [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| 5. Documentación de la base RAG | §5 de este doc |
| 6. Evidencia de ≥2 tareas ejecutadas | [`docs/EVIDENCE.md`](EVIDENCE.md) |
| 7. Capturas de observabilidad | Langfuse (traza `coding-agent-task`) — ver §7 |
| 8. Reflexión | §8 de este doc |

---

## 3. Caso de uso

**Tipo de caso (de la consigna):** *agregar una funcionalidad a un proyecto existente*.

**Proyecto objetivo:** `choppedapp_copia` — una **copia standalone** de un proyecto real
(ChoppedApp: backend NestJS + TypeScript + TypeORM, frontend React), en su **propio repo de
git/GitHub, externo al TP**. No es el ChoppedApp original ni vive dentro de este repo; el
agente lo modifica vía el `workspace` de `agent.config.yaml`.

**Objetivo concreto:** que el agente agregue una funcionalidad concreta al backend
NestJS respetando las convenciones del proyecto. Feature de referencia:
**`GET /store/items/:id`** — devolver un ítem del catálogo por id, con **404** si no
existe, más su **test unitario** del service.

**Por qué sirve para el agente:** es un repo real y no trivial (9 módulos NestJS) que el
agente debe explorar, entender y modificar siguiendo convenciones que descubre por RAG.
Las tareas de prueba (RAG+feature, memoria, cambio de estrategia) se ejecutan sobre este
workspace.

**Criterio de "cumplido" (verificable):**

1. Existe `getItem(id)` en `store.service.ts` (devuelve el ítem o lanza
   `NotFoundException`) y la ruta `@Get('items/:id')` en `store.controller.ts`.
2. Hay `store.service.spec.ts` con caso feliz + caso 404 y `npm test` (desde `backend/`) pasa.
3. El agente muestra las **fuentes del RAG** que usó para respetar las convenciones.

Definición completa en [`docs/CASO_DE_USO.md`](CASO_DE_USO.md); evidencia de las corridas
en [`docs/EVIDENCE.md`](EVIDENCE.md).

---

## 4. Arquitectura (resumen)

Detalle completo en [`docs/ARCHITECTURE.md`](ARCHITECTURE.md). En una frase:

```
Usuario → main.py → CodingAgentOrchestrator → TaskState (estado compartido)
        -> SubagentRouter -> subagentes seleccionados segun la tarea
        -> Brief compartido
        -> Harness por subagente (tools restringidas + permisos + loop guard)
        → TaskState + ProjectMemory + TraceRecorder
```

- **Agente principal (`CodingAgentOrchestrator`):** recibe la tarea, mantiene el estado,
  coordina subagentes, arma el brief y ejecuta el harness.
- **Subagentes:** `Explorer`, `Researcher`, `Implementer`, `Tester` y `Reviewer`.
  El router clasifica el pedido con el LLM, elige solo los necesarios y registra
  el motivo de seleccion o skip.
  Cada uno recibe un set propio de tools.
  Ya no se ejecuta un pipeline fijo para todos los pedidos; si `Implementer`
  no escribe cambios, `Tester` se saltea y el motivo queda en observaciones.
- **Estado compartido (`TaskState`):** pedido, progreso, resultados de subagentes, fuentes
  y tool calls etiquetadas por subagente, archivos modificados, observaciones, errores,
  iteraciones y respuesta final.
  Se serializa a `runs/task_states/<id>.json`.
- **Resultado de subagente:** `status`, `summary`, `evidence`, `files_changed`,
  `blockers` y `recommendation`.
- **Reviewer:** devuelve `approved`, `changes_requested` o `blocked`; si pide cambios,
  el orquestador no marca la tarea como completada.
- **Harness:** llama al LLM, valida permisos **antes** de cada tool call, pide aprobación
  cuando corresponde, ejecuta tools y detecta repeticiones sin avance (`loop_guard.py`).

---

## 5. Documentación de la base RAG

RAG mínimo, sin frameworks externos. Pipeline: `chunker → embeddings → vector_store → retriever`,
expuesto como la tool `rag_search`.

- **Fuentes** (`rag_docs/`, 5 documentos técnicos del ecosistema NestJS/TypeScript):
  `nestjs_controllers.md`, `nestjs_providers_di.md`, `nestjs_exceptions_validation.md`,
  `nestjs_testing_jest.md`, `typeorm_repositories.md`.
- **Chunking** (`rag/chunker.py`): por caracteres con solapamiento, `chunk_size=800`,
  `overlap=150`. Los 5 docs generan **15 chunks**.
- **Embeddings** (`rag/embeddings.py`): API de OpenAI, modelo `text-embedding-3-small`.
- **Almacenamiento** (`rag/vector_store.py`): índice JSON local en
  `storage/vector_store/index.json` (source, chunk_id, texto, embedding).
- **Recuperación** (`rag/retriever.py`): similitud **coseno**, `top_k=3` por defecto. La tool
  devuelve cada resultado con `Fuente`, `Chunk`, `Score` y `Contenido`, para que las
  afirmaciones sean verificables y se distinga la fuente (RAG vs repo vs memoria vs web).
- **Política:** el harness aplica RAG-first en runtime: `web_search` se bloquea
  hasta que el subagente haya intentado `search_rag`/`rag_search`. Ingesta:
  `PYTHONPATH=src python -m coding_agent.rag.ingest`.

---

## 7. Observabilidad

Cada corrida se registra en `TraceRecorder`: prompts, modelo, spans por subagente,
llamadas al LLM, tools, fuentes RAG/web, iteraciones, errores, latencia, tokens,
costo estimado y resultado final. Guarda
**trazas locales** en `runs/traces/<id>.json` (independiente de servicios externos) y exporta
a **Langfuse**.

Config del `.env` (SDK v3 lee `LANGFUSE_HOST`, **no** `LANGFUSE_BASE_URL`; región del proyecto: US):

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

Para la captura (entregable 7): dashboard de Langfuse → filtrar por nombre `coding-agent-task`
→ abrir una traza (muestra el árbol de spans: `agent-explorer`,
`agent-implementer`, etc., con sus iteraciones LLM, tool calls, resultados,
tokens, latencia y costo). Los `task_id` de cada corrida están en [`docs/EVIDENCE.md`](EVIDENCE.md).

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
- **RAG específico del ecosistema.** Al apuntar el RAG a docs de NestJS/TypeScript, el agente
  respeta convenciones del repo objetivo (lanzar `NotFoundException` en vez de devolver
  `null`) que no infiere solo del código.
- **Router de subagentes + tools por rol.** No se ejecuta un pipeline fijo: el router
  clasifica la tarea con el LLM, valida la salida contra los roles conocidos y cada
  subagente tiene su set de tools; el Tester se saltea si el Implementer no escribió nada.

### Qué falló / aristas ásperas

- **Config de Langfuse frágil.** El `.env` usaba `LANGFUSE_BASE_URL` (el SDK v3 lee
  `LANGFUSE_HOST`) y tenía una comilla sin cerrar que metía un `\n` en el host y rompía el
  DNS. El error visible (`timeout`/`401`) no señalaba la causa real.
- **Manejo de excepciones del trace.** En una corrida la tarea de estrategia terminó `blocked`
  con `"generator didn't stop after throw()"`: una excepción dentro de `trace.trace_task()`
  no se maneja limpio.
- **Loop guard sin corte duro.** El loop guard avisa pero no frena; el corte real lo hace el
  tope `max_iterations`, y una corrida llegó a escribir la feature pero se quedó sin
  iteraciones antes del test unitario.

### Cuándo se detectaron loops o falta de evidencia

- **Loop:** en la tarea "arreglá `payments.service.ts`", el agente repite `list_files` sobre una
  ruta inexistente; el **loop guard lo detecta** ("repeated action... change strategy or ask
  for help") y el agente deja de repetir.
- **Falta de evidencia:** el módulo `payments` no existe en el backend; el agente lo
  **reconoce y pide ayuda** en lugar de inventar un fix, y el Tester se saltea (no hubo
  `write_file`).

### Qué mejoraríamos

1. **Tope duro de iteraciones por turno** (no solo el nudge del loop guard) y manejo de
   excepciones limpio en `trace_task` (arreglar el `generator didn't stop`).
2. **Correr los tests del repo objetivo desde el agente** y realimentar el resultado al ciclo.
3. **Más cobertura del RAG** de NestJS (guards/JWT, DTOs con `class-validator`, TypeORM avanzado).
4. **Contexto:** resumen de historial con LLM para tareas y repos grandes.
5. **Extra opcional:** sistema de plugins de tools con autodescubrimiento.
