# TP Coding Agent Avanzado

Coding agent modular en Python para trabajar sobre un repositorio objetivo con
subagentes, tools locales, RAG, memoria persistente, politicas de seguridad,
estado compartido y trazas locales/Langfuse.

Este README contiene las instrucciones de instalacion, configuracion y
ejecucion del proyecto.

## Requisitos

- Python 3.11 o superior.
- Cuenta y API key de OpenAI.
- API key de Tavily para habilitar `web_search`.
- Proyecto de Langfuse para ver las trazas en el dashboard.

## Instalacion

Desde la raiz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuracion

Crear un archivo `.env` en la raiz del repositorio con estas variables:

```env
OPENAI_API_KEY=
TAVILY_API_KEY=
MODEL=gpt-5-nano
EMBEDDING_MODEL=text-embedding-3-small
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

Usar el `LANGFUSE_HOST` de la region de tu proyecto, por ejemplo
`https://cloud.langfuse.com` o `https://us.cloud.langfuse.com`. El SDK lee
`LANGFUSE_HOST`.

Despues ajustar `agent.config.yaml`:

```yaml
workspace: C:/ruta/al/repositorio/objetivo

memory:
  path: ./memory/project_memory.json

observability:
  provider: langfuse
  local_traces_path: ./runs/traces

orchestrator:
  max_iterations: 20
```

La clave `workspace` apunta al repositorio sobre el que trabaja el agente. Las
rutas de memoria, estados y trazas pueden dejarse como vienen o cambiarse a otra
ubicacion local.

## RAG

Los documentos locales viven en `rag_docs/`. Para generar el indice vectorial:

```powershell
$env:PYTHONPATH = "src"
python -m coding_agent.rag.ingest
```

El indice se guarda en `storage/vector_store/index.json` y lo usa la tool
`search_rag`.

## Ejecucion

Activar el entorno virtual y ejecutar el agente interactivo:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python -m coding_agent.main
```

Comandos disponibles dentro del chat:

- `/plan`: activa o desactiva la aprobacion manual de plan antes de ejecutar.
- `/supervision`: activa o desactiva aprobacion manual para tools supervisadas.
- `/exit`: cierra la sesion.

Cada pedido del usuario genera:

- `runs/task_states/<task_id>.json`: estado compartido de la tarea.
- `runs/traces/<task_id>.json`: traza local completa.
- una traza `coding-agent-task` en Langfuse cuando las credenciales estan
  configuradas.

## Generar Evidencia

El script de evidencia ejecuta los casos del trabajo practico contra el
repositorio configurado en `workspace`:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/generate_evidence.py
```

Al finalizar imprime los `task_id` generados y las rutas de sus archivos en
`runs/task_states/` y `runs/traces/`.

## Tests

Para correr la suite:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = "src"
python -m unittest discover tests
```
