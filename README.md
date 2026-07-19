# TP Coding Agent Avanzado

Proyecto para el TP final de Coding Agent Avanzado.

El objetivo es construir un coding agent modular en Python, sin frameworks de
orquestacion como LangChain, LangGraph, CrewAI o AutoGen. El agente tiene
subagentes, tools locales, RAG, memoria persistente, politicas de seguridad,
estado compartido y observabilidad con Langfuse.

## Estado Actual

Ya esta implementado:

- Arquitectura modular en `src/coding_agent/`.
- Orquestador central en `runtime/orchestrator.py`.
- Harness propio para el loop LLM -> tools -> resultados -> LLM.
- Estado compartido con `TaskState`.
- Subagentes especializados con ruteo por tarea y tools propias por rol.
- Tools registradas para el LLM.
- Registry de tools con scopes por subagente.
- RAG minimo sobre documentacion local.
- Politica RAG-first aplicada por runtime: `web_search` se bloquea hasta que
  el subagente haya intentado `search_rag`.
- Memoria persistente por proyecto.
- Observabilidad local y exportacion a Langfuse.
- Prueba end-to-end reproducible.
- Tests unitarios basicos.
- Caso de uso inicial en `cases/football_predictor/`.

## Estructura General

```text
src/coding_agent/
  agents/
  core/
  llm/
  memory/
  observability/
  prompts/
  rag/
  runtime/
  security/
  tools/
  main.py

cases/football_predictor/
rag_docs/
docs/
scripts/
tests/
```

## Flujo Del Agente

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

`main.py` queda simple a proposito. Solo carga configuracion, construye el
orquestador y ejecuta el chat.

La coordinacion real vive en:

```text
src/coding_agent/runtime/orchestrator.py
```

## Componentes Principales

### `core/`

Contiene las abstracciones y el estado compartido del agente:

- `contracts.py`: contratos vivos `AgentContext`, `AgentState` y `MemoryStore`.
- `task_state.py`: estado compartido de cada tarea, con evidencia etiquetada
  por subagente cuando viene de tools.
- `config.py`: carga de configuracion YAML.

El codigo operativo vive en paquetes especificos (`runtime`, `llm`, `security`)
para evitar que `core` se convierta en una carpeta con responsabilidades
mezcladas.

### `runtime/`

Contiene la ejecucion del agente:

- `orchestrator.py`: coordina conversacion, memoria, plan mode, supervision, trazas y ejecucion.
- `orchestrator_settings.py`: configuracion runtime del orquestador.
- `harness.py`: loop principal LLM -> tools -> resultados -> LLM.
- `loop_guard.py`: deteccion de acciones repetidas sin avance.
- `io.py`: frontera de entrada/salida.

### `llm/`

Contiene adaptadores y helpers de modelo:

- `client.py`: adapter para OpenAI.
- `planner.py`: generacion de planes sin ejecutar tools.

### `security/`

Contiene la logica de seguridad:

- `permissions.py`: validacion de permisos de archivos y comandos.
- `supervision.py`: aprobacion humana para acciones riesgosas.

### `agents/`

Contiene agentes especializados:

- `specs.py`: define responsabilidad, prompt y tools permitidas por subagente.
- `router.py`: selecciona solo los subagentes utiles para el pedido y explica
  por que selecciono o salteo cada rol.
- `results.py`: normaliza la salida de cada subagente como resultado estructurado.
- `Explorer`: entiende estructura, arquitectura, dependencias y archivos relevantes.
- `Researcher`: consulta RAG primero, memoria del proyecto y web solo si falta evidencia.
- `Implementer`: aplica cambios concretos y acotados. Si falta evidencia o el pedido es ambiguo, no escribe.
- `Tester`: valida con comandos reales y se detiene si repite acciones sin avanzar.
- `Reviewer`: revisa el diff real contra el pedido original y decide
  `approved`, `changes_requested` o `blocked`, sin permiso de escritura.
- `AgentPipeline`: mantiene el nombre historico, pero ahora coordina ruteo y ejecucion de subagentes seleccionados.

El router no ejecuta todos los subagentes por costumbre. `Explorer` se usa para
tareas que requieren contexto del repo; `Researcher` se usa cuando hace falta
evidencia tecnica, RAG, memoria o web. En tareas de implementacion, si
`Implementer` termina sin un `write_file` exitoso, `Tester` se saltea y queda
registrada una observacion en `TaskState`.

Cada subagente devuelve `status`, `summary`, `evidence`, `files_changed`,
`blockers` y `recommendation`. Las fuentes y tool calls quedan registradas con
el subagente responsable para que el brief final no pierda trazabilidad. Si
`Reviewer` pide cambios, la tarea queda como `changes_requested` y la respuesta
final lo aclara.

Tools permitidas por rol:

```text
Explorer:    list_files, read_file, search_rag, read_project_memory
Researcher:  search_rag, web_search, read_project_memory
Implementer: read_file, write_file, list_files
Tester:      run_command, read_file
Reviewer:    read_file, run_command
```

### `tools/`

Tools registradas para el LLM:

```text
read_file
write_file
run_command
list_files
web_search
tree_files
search_code
view_file
rag_search
search_rag
remember_decision
remember_command
memory_context
read_project_memory
```

`web_search` no queda librada solo al prompt: el harness aplica una politica
RAG-first. Si un subagente intenta usar web sin haber llamado antes a
`search_rag` o `rag_search`, la tool se bloquea y queda registrada como
`allowed=False` en `TaskState.tool_calls`.

### `rag/`

RAG minimo sin frameworks externos:

- `chunker.py`: divide documentos.
- `embeddings.py`: genera embeddings con OpenAI.
- `vector_store.py`: guarda y busca en indice JSON local.
- `ingest.py`: indexa documentos de `rag_docs/`.
- `retriever.py`: recupera chunks por similitud coseno.

### `memory/`

Memoria separada en capas:

- `ConversationMemory`: mensajes de la sesion actual.
- `ExecutionMemory`: tareas completadas durante el proceso actual.
- `ProjectMemory`: memoria persistente auditable en JSON.
- `PersistentMemoryStore`: adapter/repository sobre `ProjectMemory`.

La memoria persistente guarda:

- memoria semantica: decisiones y hechos del proyecto;
- memoria procedural: comandos utiles;
- memoria episodica: historial de tareas.

### `observability/`

`TraceRecorder` registra:

- prompts,
- modelo usado,
- llamadas al LLM,
- tools invocadas,
- documentos RAG recuperados,
- busquedas web,
- iteraciones,
- errores,
- latencia,
- tokens,
- costo estimado,
- resultado final.

Tambien exporta a Langfuse si las variables de entorno estan configuradas.

## Instalacion

Crear y activar entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Crear `.env` usando `.env.example` como referencia.

Variables esperadas:

```env
OPENAI_API_KEY=
TAVILY_API_KEY=
MODEL=gpt-5-nano
EMBEDDING_MODEL=text-embedding-3-small

LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

> El SDK de Langfuse v3 lee **`LANGFUSE_HOST`** (no `LANGFUSE_BASE_URL`). Usar la región
> correcta del proyecto: `https://cloud.langfuse.com` (EU) o `https://us.cloud.langfuse.com`
> (US). No poner comillas ni espacios en los valores.

No commitear `.env`.

## Configuracion

La configuracion principal esta en:

```text
agent.config.yaml
```

Define:

- workspace del caso de uso;
- ruta de memoria;
- proveedor de observabilidad;
- precios estimados por modelo;
- rutas bloqueadas para lectura/escritura;
- comandos prohibidos;
- comandos que requieren aprobacion.

Actualmente el workspace configurado es:

```text
./cases/football_predictor
```

## Ejecutar El Agente

Desde la raiz del repo:

```powershell
$env:PYTHONPATH="src"
python -m coding_agent.main
```

Comandos interactivos:

```text
/plan
/supervision
/exit
```

- `/plan`: pide un plan antes de ejecutar.
- `/supervision`: pide aprobacion para acciones riesgosas.
- `/exit`: cierra el chat.

## RAG

Los documentos fuente viven en:

```text
rag_docs/
```

Ingestar documentos:

```powershell
$env:PYTHONPATH="src"
python -m coding_agent.rag.ingest
```

Esto genera:

```text
storage/vector_store/index.json
```

Buscar desde Python:

```python
from coding_agent.rag.retriever import rag_search

print(rag_search("como evitar data leakage con pandas"))
```

## Memoria

La memoria se guarda en:

```text
memory/project_memory.json
```

El agente puede actualizarla mediante:

```text
remember_decision
remember_command
memory_context
```

La idea es guardar hitos o decisiones importantes, no cada microaccion.

## Observabilidad Y Prueba End-To-End

Hay una prueba end-to-end en:

```text
scripts/run_e2e_smoke.py
```

Comando:

```powershell
$env:PYTHONPATH="src"
python scripts/run_e2e_smoke.py
```

La prueba usa:

- memoria persistente;
- RAG local;
- tool de inspeccion del repo;
- busqueda web con Tavily;
- llamada real al LLM;
- trazas locales;
- exportacion a Langfuse.

Evidencia generada:

```text
runs/task_states/<task_id>.json
runs/traces/<task_id>.json
memory/project_memory.json
Langfuse dashboard
```

Esta prueba no debe correr como test unitario porque llama APIs externas.

## Tests

Tests unitarios:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Actualmente cubren:

- pipeline de agentes;
- harness con LLM falso y tool inyectada;
- memoria persistente;
- permisos;
- RAG/vector store local;
- funciones de tools y registry.

Compilacion completa:

```powershell
.\.venv\Scripts\python.exe -m compileall src cases\football_predictor tests scripts
```

## Caso De Uso

El caso de uso inicial vive en:

```text
cases/football_predictor/
```

La idea del caso es predecir resultados de partidos entre selecciones con
probabilidades, usando features como Elo, ranking FIFA, forma reciente,
goles, head-to-head y localia.

Comandos utiles:

```powershell
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France
python cases/football_predictor/scripts/evaluate.py
```

El agente debe mantenerse general. El conocimiento especifico de futbol debe
vivir en `cases/football_predictor/` y `rag_docs/`, no hardcodeado en el core.

## Documentacion Interna

Mas contexto:

```text
docs/ARCHITECTURE.md
docs/E2E_SMOKE_TEST.md
docs/EVIDENCE_TEMPLATE.md
docs/NEXT_STEPS.md
```

## Archivos Que No Se Versionan

No se deben commitear:

```text
.env
.venv/
memory/project_memory.json
runs/task_states/*.json
runs/traces/*.json
storage/vector_store/
```

Estos archivos son locales, generados o contienen informacion sensible.

## Que Queda Por Hacer

Prioridad alta:

- Capturar y guardar evidencia final de una o dos corridas en Langfuse.
- Completar el caso de uso `football_predictor` con datasets reales y evaluacion clara.
- Documentar en la entrega que el agente general no tiene logica de futbol hardcodeada.

Prioridad media:

- Agregar mas tests sobre `orchestrator.py`.
- Agregar una prueba controlada donde el agente interactivo use `rag_search`, `web_search` y memoria.
- Mejorar el README del caso de uso especifico dentro de `cases/football_predictor/`.

Prioridad baja:

- Refinar costos estimados si se cambia de modelo.
- Agregar mas documentos a `rag_docs/`.
- Mejorar mensajes de error para configuraciones incompletas.
