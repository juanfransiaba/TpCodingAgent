# E2E Smoke Test

Este script ejecuta una prueba end-to-end del agente sin depender del modo
interactivo.

Comando:

```powershell
$env:PYTHONPATH="src"
python scripts/run_e2e_smoke.py
```

La prueba usa:

- memoria persistente (`memory_context` y guardado posterior),
- RAG local (`rag_search`),
- inspeccion del repo (`tree_files`),
- busqueda web con Tavily (`web_search`),
- una llamada real al LLM configurado,
- trazas locales,
- exportacion a Langfuse si las keys estan configuradas.

Evidencia generada:

- `runs/task_states/<task_id>.json`
- `runs/traces/<task_id>.json`
- `memory/project_memory.json`
- trace en el dashboard de Langfuse, si esta habilitado.

No debe correr como test unitario porque llama APIs externas.
