# Arquitectura Del Coding Agent

## Objetivo

El sistema implementa un coding agent avanzado sin frameworks de orquestacion como LangChain, LangGraph, CrewAI o AutoGen.

El agente combina:

- harness propio,
- tools locales,
- subagentes especializados con ruteo y tools propias,
- estado compartido,
- memoria persistente,
- RAG,
- politicas de seguridad,
- observabilidad.

## Flujo general

```text
Usuario
  -> main.py
  -> runtime/CodingAgentOrchestrator
  -> TaskState
  -> SubagentRouter
  -> subagentes seleccionados segun la tarea
  -> Brief compartido
  -> Harness por subagente con tools restringidas
  -> respuesta final
  -> TaskState + ProjectMemory + TraceRecorder
```

`main.py` queda intencionalmente fino: carga configuracion, construye el
orquestador y ejecuta el chat. La coordinacion real vive en:

```text
src/coding_agent/runtime/orchestrator.py
```

## Abstracciones core

El paquete `core/` queda reservado para contratos, estado compartido y carga de
configuracion.

Archivo principal:

```text
src/coding_agent/core/contracts.py
```

Define los contratos principales:

- `AgentContext`
- `AgentState`
- `MemoryStore`

Estas abstracciones permiten compartir contexto, estado y memoria sin acoplar
el harness o los subagentes a implementaciones concretas.

## Mapa De Paquetes

```text
src/coding_agent/
  core/          contratos, TaskState y config
  runtime/       orquestador, harness, IO y loop guard
  llm/           cliente OpenAI y planificacion
  security/      permisos y supervision humana
  agents/        specs, router, coordinator y subagentes
  tools/         tools concretas y registry para el LLM
  rag/           ingesta, embeddings, vector store y retrieval
  memory/        memoria conversacional, ejecucion y persistente
  observability/ trazas locales y Langfuse
  prompts/       prompts por rol
```

El codigo operativo vive en paquetes especificos (`runtime`, `llm`, `security`)
para evitar mezclar responsabilidades dentro de `core`.

## Runtime

Paquete principal de ejecucion:

```text
src/coding_agent/runtime/
```

Responsabilidades:

- `orchestrator.py`: coordinar la sesion interactiva.
- `orchestrator_settings.py`: centralizar settings runtime.
- `harness.py`: ejecutar el loop LLM -> tools -> resultados -> LLM.
- `loop_guard.py`: detectar repeticiones sin avance.
- `io.py`: separar consola del orquestador.

## Harness

Archivo principal:

```text
src/coding_agent/runtime/harness.py
```

Responsabilidades:

- llamar al LLM,
- detectar tool calls,
- validar permisos,
- pedir aprobacion cuando corresponde,
- ejecutar tools,
- detectar repeticiones sin avance mediante loop guard,
- devolver resultados al LLM,
- repetir hasta respuesta final.

El loop guard vive en:

```text
src/coding_agent/runtime/loop_guard.py
```

Si una tool devuelve el mismo resultado con argumentos equivalentes varias veces, el agente recibe una observacion para cambiar de estrategia, replanificar o pedir ayuda.

## Estado compartido

Archivo:

```text
src/coding_agent/core/task_state.py
```

`TaskState` registra:

- pedido original,
- estado de la tarea,
- progreso,
- resultados de subagentes,
- fuentes, con subagente y query cuando vienen de RAG/web,
- archivos modificados,
- observaciones,
- tool calls, con subagente responsable,
- errores,
- iteraciones,
- respuesta final.

## Subagentes

Carpeta:

```text
src/coding_agent/agents/
```

Roles:

- `SubagentSpec`: define metadata declarativa: responsabilidad, prompt, tools
  permitidas y limite de iteraciones.
- `subagents/base.py` y clases concretas en archivos por rol (`explorer.py`,
  `researcher.py`, `implementer.py`, `tester.py`, `reviewer.py`): encapsulan
  el comportamiento de cada rol, incluyendo armado de mensajes, trazas, skip y
  post-proceso.
- `SubagentRegistry`: resuelve el nombre seleccionado por el router a una
  instancia concreta de subagente.
- `SubagentRouter`: coordina clasificacion LLM, parseo y policy de ruteo para
  devolver un `RoutePlan` validado con subagentes seleccionados, subagentes
  salteados y el motivo de cada decision. Si el LLM falla o devuelve JSON
  invalido, la tarea falla explicitamente en vez de inventar una ruta local.
- `SubagentRunResult`: normaliza la respuesta de cada subagente como `status`,
  `summary`, `evidence`, `files_changed`, `blockers` y `recommendation`.
- `Explorer`: entiende estructura, arquitectura, dependencias, convenciones y archivos relevantes.
- `Researcher`: investiga informacion tecnica con RAG primero, memoria del proyecto y web solo como fallback.
- `Implementer`: aplica cambios concretos y acotados desde la evidencia disponible. Si falta evidencia o el pedido es ambiguo, no escribe.
- `Tester`: valida cambios con comandos reales como tests, build o lint, y se detiene si repite acciones sin avanzar.
- `Reviewer`: revisa el diff real contra el pedido original y devuelve una
  decision formal: `approved`, `changes_requested` o `blocked`, sin permiso de
  escritura.

El `SubagentCoordinator` no ejecuta un flujo fijo ni contiene comportamiento
especifico de roles. Coordina un ruteo por tarea decidido por el clasificador
LLM del router, busca cada rol en `SubagentRegistry` y delega la ejecucion a la
clase concreta. Por ejemplo, una tarea de investigacion puede usar solo
`Researcher`, mientras que una tarea de cambio de codigo puede usar `Explorer ->
Implementer -> Tester -> Reviewer` y sumar `Researcher` solo si el pedido
requiere documentacion, RAG, memoria o web.

El ruteo tambien aplica invariantes de arquitectura. Si el LLM selecciona
`Implementer`, el router garantiza `Explorer`, `Tester` y `Reviewer` alrededor
del cambio. Si selecciona `Tester`, garantiza `Reviewer`. Despues, si
`Implementer` no produjo ningun `write_file` exitoso, `TesterSubagent` decide
saltearse; el motivo queda registrado en `TaskState.observations`.

Si `Reviewer` devuelve `changes_requested`, el orquestador conserva ese estado
en lugar de marcar la tarea como `completed`, y antepone una advertencia a la
respuesta final. Si devuelve `blocked`, la tarea queda bloqueada.

Cada subagente recibe un scope propio de tools:

```text
Explorer:    list_files, read_file, search_rag, read_project_memory
Researcher:  search_rag, web_search, read_project_memory
Implementer: read_file, write_file, list_files
Tester:      run_command, read_file
Reviewer:    read_file, run_command
```

El harness ejecuta tools, permisos, supervision y loop guard, pero no decide el
set de tools. El set lo define el subagente seleccionado.

Antes de ejecutar `web_search`, el harness tambien aplica la politica
RAG-first de `security/evidence_policy.py`: el mismo subagente debe haber
registrado antes una llamada permitida a `search_rag` o `rag_search`. Si no,
la llamada web se bloquea y queda auditada en `TaskState.tool_calls`.

## Tools

Carpeta:

```text
src/coding_agent/tools/
```

Tools base:

- `read_file`
- `write_file`
- `run_command`
- `list_files`
- `web_search`

Tools agregadas:

- `tree_files`
- `search_code`
- `view_file`
- `rag_search`
- `search_rag`
- `remember_decision`
- `remember_command`
- `memory_context`
- `read_project_memory`

Las tools pasan por validacion de permisos antes de ejecutarse.

## Politicas

Archivo:

```text
agent.config.yaml
```

Define:

- workspace,
- memoria,
- observabilidad,
- rutas bloqueadas para lectura/escritura,
- comandos prohibidos,
- comandos que requieren aprobacion.
- politica dinamica RAG-first para impedir `web_search` sin intento previo de
  RAG.

## Memoria persistente

Archivo:

```text
src/coding_agent/memory/project_memory.py
```

Tres capas:

- semantica: decisiones y hechos,
- procedural: comandos utiles,
- episodica: resumen de tareas anteriores.

Se guarda en:

```text
memory/project_memory.json
```

El agente tambien puede actualizar memoria mediante tools:

- `remember_decision`: guarda decisiones durables.
- `remember_command`: guarda comandos utiles.
- `memory_context`: recupera memoria compacta.

La memoria quedo separada en capas:

- `ConversationMemory`: historial de mensajes de la sesion actual.
- `ExecutionMemory`: tareas completadas durante el proceso actual.
- `PersistentMemoryStore`: adapter/repository sobre `ProjectMemory`.

## RAG

Carpeta:

```text
src/coding_agent/rag/
```

Componentes:

- `chunker.py`: divide documentos.
- `embeddings.py`: genera embeddings con OpenAI.
- `vector_store.py`: guarda/carga indice JSON.
- `ingest.py`: ingesta `rag_docs/`.
- `retriever.py`: busca por similitud coseno.

Docs fuente:

```text
rag_docs/
```

Indice generado:

```text
storage/vector_store/index.json
```

## Observabilidad

Archivo:

```text
src/coding_agent/observability/tracing.py
```

Integra Langfuse y guarda trazas locales.

Registra:

- prompts,
- modelo,
- spans por subagente,
- llamadas al LLM,
- tools,
- RAG/web sources,
- iteraciones,
- errores,
- latencia,
- tokens,
- costo estimado,
- resultado final.

En Langfuse el span raiz `coding-agent-task` contiene un span por subagente
(`agent-explorer`, `agent-implementer`, etc.). Las generaciones LLM y tool calls
del harness se crean dentro de ese contexto, por lo que quedan anidadas bajo el
subagente responsable y tambien mantienen `agent_name` en metadata.
La clasificacion inicial del router se registra como `router-classification`.

## Caso de uso

El repo objetivo es `choppedapp_copia`, un **repo propio y externo** (copia
standalone de ChoppedApp: NestJS + React), con su propio git/GitHub. No vive dentro
del TP; el agente lo modifica via el `workspace` de `agent.config.yaml`:

```text
workspace: /Users/thiagoserebrinsky/facultad/projects/copiaDeChoppedApp/choppedapp_copia
```

El objetivo del agente es **agregar una funcionalidad concreta** al backend NestJS.
Definicion, objetivo y criterio de cumplido en `docs/CASO_DE_USO.md`.

El agente es general. El conocimiento especifico del caso vive en el repo objetivo y
en `rag_docs/`, no hardcodeado en el core.
