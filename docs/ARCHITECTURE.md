# Arquitectura Del Coding Agent

## Objetivo

El sistema implementa un coding agent avanzado sin frameworks de orquestacion como LangChain, LangGraph, CrewAI o AutoGen.

El agente combina:

- harness propio,
- tools locales,
- subagentes especializados,
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
  -> MainAgent
  -> Explorer/Researcher
  -> AgentPipeline
  -> PlannerAgent -> CoderAgent -> TestAgent -> ReviewerAgent
  -> Brief compartido
  -> Harness
  -> LLM + tools
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

- `Agent`
- `AgentState`
- `AgentResult`
- `Tool`
- `LLMClient`
- `MemoryStore`
- `Retriever`
- `Orchestrator`

Estas abstracciones permiten aplicar dependency injection sin acoplar el
harness o los agentes a implementaciones concretas.

## Mapa De Paquetes

```text
src/coding_agent/
  core/          contratos, TaskState y config
  runtime/       orquestador, harness, IO y loop guard
  llm/           cliente OpenAI y planificacion
  security/      permisos y supervision humana
  agents/        subagentes y pipeline
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
- fuentes,
- archivos modificados,
- observaciones,
- tool calls,
- errores,
- iteraciones,
- respuesta final.

## Subagentes

Carpeta:

```text
src/coding_agent/agents/
```

Roles:

- `Explorer`: entiende estructura, archivos relevantes y metadata del repo.
- `Researcher`: registra fuentes locales, memoria y contexto RAG/web cuando aplique.
- `PlannerAgent`: interpreta la tarea y propone el flujo de trabajo.
- `CoderAgent`: define el enfoque de implementacion.
- `TestAgent`: propone comandos de validacion.
- `ReviewerAgent`: revisa riesgos, errores, evidencia y cumplimiento del pedido.

El `MainAgent` coordina `Explorer` y `Researcher` como agentes de evidencia, y
despues ejecuta `AgentPipeline` con el flujo:

```text
planificar -> implementar -> testear -> revisar
```

La arquitectura usa directamente las clases especializadas nuevas, sin mantener
modulos duplicados para los roles viejos.

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
- `remember_decision`
- `remember_command`
- `memory_context`

Las tools pasan por validacion de permisos antes de ejecutarse.

Ademas hay wrappers tipo Command para que la arquitectura tenga herramientas
con una interfaz comun:

- `FileTool`
- `TerminalTool`
- `GitTool`
- `TestRunnerTool`
- `CodeSearchTool`

Estos wrappers no reemplazan al registry de OpenAI; lo complementan. El LLM
sigue usando `tool_registry.py`, mientras que el sistema puede inyectar tools
concretas cuando necesite una interfaz de objetos.

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
- llamadas al LLM,
- tools,
- RAG/web sources,
- iteraciones,
- errores,
- latencia,
- tokens,
- costo estimado,
- resultado final.

## Caso de uso

El caso inicial esta en:

```text
cases/football_predictor/
```

El agente es general. El conocimiento especifico del caso vive en `cases/` y `rag_docs/`, no hardcodeado en el core.
