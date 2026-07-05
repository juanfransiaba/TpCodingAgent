# Next Steps

Este documento resume lo que falta despues de las ultimas mejoras del agente.

## Estado Actual

Ya esta funcionando:

- agente modular con orquestador, subagentes y harness propio;
- RAG local con ingesta y retrieval;
- memoria persistente;
- tools de repo, comandos, archivos, web, RAG y memoria;
- observabilidad local y Langfuse;
- prueba end-to-end en `scripts/run_e2e_smoke.py`;
- tests unitarios basicos;
- regla RAG-first en el system prompt.

## Prioridad Alta

### 1. Dataset real del caso

Hoy solo existe:

```text
cases/football_predictor/data/results_sample.csv
```

Para la entrega hace falta agregar:

```text
cases/football_predictor/data/results.csv
```

Debe tener estas columnas:

```text
date
home_team
away_team
home_score
away_score
tournament
city
country
neutral
```

### 2. Prediccion y evaluacion reales

Cuando este el dataset:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France --data cases/football_predictor/data/results.csv
```

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/evaluate.py --data cases/football_predictor/data/results.csv
```

Guardar la salida para la entrega.

### 3. Evidencia de Langfuse

Capturar al menos una traza completa donde se vea:

- prompt;
- modelo;
- tool calls;
- RAG docs recuperados;
- web search;
- memoria;
- latencia;
- tokens/costo si estan disponibles;
- resultado final.

La prueba end-to-end ya ayuda con esto:

```powershell
$env:PYTHONPATH="src"
python scripts/run_e2e_smoke.py
```

### 4. Segunda tarea de evidencia

Ya hay evidencia de una tarea con RAG. Falta una segunda tarea que demuestre
memoria persistente o cambio de estrategia.

Prompt sugerido para memoria:

```text
Segun la memoria del proyecto, que regla o decision importante se registro sobre data leakage?
```

Prompt sugerido para cambio de estrategia:

```text
Intenta ejecutar la evaluacion del predictor. Si falla por falta del dataset real, explica que evidencia falta y propone una alternativa segura.
```

## Prioridad Media

### 5. Redaccion final

Escribir la narrativa de entrega:

- caso de uso;
- criterio de tarea cumplida;
- arquitectura;
- RAG;
- memoria;
- observabilidad;
- reflexion final.

Material ya disponible:

```text
README.md
ESTADO_Y_PENDIENTES.md
docs/ARCHITECTURE.md
docs/E2E_SMOKE_TEST.md
cases/football_predictor/README.md
```

### 6. Tests adicionales

Opcionalmente sumar tests para:

- `CodingAgentOrchestrator`;
- manejo de errores en observabilidad;
- permisos de commands con mas casos borde.

## Prioridad Baja

- Agregar mas documentos a `rag_docs/`.
- Mejorar autodescubrimiento de tools estilo plugin.
- Refinar costos estimados si se cambia de modelo.
