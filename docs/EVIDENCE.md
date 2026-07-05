# Evidencias de corridas (TP Coding Agent Avanzado)

Corridas reales ejecutadas sobre el caso `football_predictor`. Todas generan traza local
en `runs/traces/<task_id>.json` y estado en `runs/task_states/<task_id>.json`.

> **Langfuse:** operativo. Las trazas suben al proyecto (región **US**,
> `https://us.cloud.langfuse.com`) además de guardarse localmente. Buscar en el dashboard por
> nombre `coding-agent-task` (el `task_id` va en el metadata de cada traza). Reproducir con
> `PYTHONPATH=src python scripts/generate_evidence.py`.
>
> Config correcta en `.env` (el SDK v3 lee `LANGFUSE_HOST`, **no** `LANGFUSE_BASE_URL`):
> ```env
> LANGFUSE_PUBLIC_KEY=pk-lf-...
> LANGFUSE_SECRET_KEY=sk-lf-...
> LANGFUSE_HOST=https://us.cloud.langfuse.com
> ```

---

## Corrida 1 — Consulta con RAG mostrando fuentes (Tarea 1)

### Prompt / llamada
```text
rag_search("como evitar data leakage al calcular features temporales con pandas", top_k=3)
```

### Capacidades observadas
- **RAG:** recupera chunks del índice local `storage/vector_store/index.json` (5 docs / 8 chunks).
- **Fuentes:** se muestran con su score de similitud coseno.

### Fuentes recuperadas
| Fuente | Chunk | Score |
| --- | --- | --- |
| `rag_docs/data_leakage.md` | 0 | 0.50 |
| `rag_docs/pandas.md` | 0 | 0.47 |

### Qué se observa
El agente prioriza el RAG local (regla "rag_search primero, web como fallback" en el
`SYSTEM_PROMPT`) y expone la evidencia con su fuente, no una respuesta a ciegas.

---

## Corrida 2 — Uso de memoria persistente (Tarea 2)

- **task_id:** `d0b738bc31224c77967824c2d596000d` (traza `coding-agent-task` en Langfuse)
- **Iteraciones:** 2 · **Tools:** `memory_context` (1)

### Prompt usado
```text
Usando la memoria persistente del proyecto (llama a la tool memory_context), decime de
donde sacamos el dataset de futbol y con que comando evaluamos los modelos. Aclara
explicitamente que esa informacion viene de la memoria del proyecto.
```

### Output relevante
```text
A partir de la memoria persistente del proyecto [...] Esta información proviene
explícitamente de la memoria del proyecto.
- Fuente del dataset: dataset_futbol -> martj42 'International football results 1872-2026'
  como cases/football_predictor/data/results.csv
- Comando para evaluar: python cases/football_predictor/scripts/evaluate.py --max-eval 300
```

### Qué se observa
El agente lee la memoria semántica (decisión `dataset_futbol`) y procedural (comando de
evaluación) via `memory_context` y las cita, distinguiendo que provienen de la memoria y
no de inferencia propia.

---

## Corrida 3 — Loop detectado + cambio de estrategia / pedir ayuda

- **task_id:** `6807bf8a0d3546f18693708234c6eb6d` (traza `coding-agent-task` en Langfuse)
- **Iteraciones:** 12 · el **loop guard se disparó** durante la corrida:
  > "Repeated action detected: list_files returned the same result 3 times with equivalent
  > arguments. Change strategy, use a different source of evidence, replan, or ask the user
  > for help."

### Prompt usado
```text
Arregla el bug del modulo de pagos en
cases/football_predictor/src/football_predictor/payments.py que hace fallar las
transacciones con tarjeta.
```

### Output relevante
```text
No puedo localizar el archivo cases/football_predictor/src/football_predictor/payments.py
en el estado actual de mi entorno. He intentado listar/recorrer esa ruta varias veces y no
aparece el archivo [...] Tampoco tengo suficientes evidencias [...]
```

### Qué se observa
El pedido no tiene evidencia real en el repo (el módulo no existe). El agente explora, repite
`list_files` sobre la misma ruta y el **loop guard lo detecta** ("repeated action... change
strategy or ask the user for help"). El agente entonces **deja de repetir**, **no inventa un
fix** y **pide ayuda** reconociendo la falta de evidencia — las dos conductas pedidas por la
consigna (detección de loop + detenerse / pedir ayuda) en una sola corrida.

> Nota: el comportamiento es no-determinista. En otra corrida el mismo prompt terminó
> `blocked` con `"generator didn't stop after throw()"` (arista áspera del manejo de
> excepciones dentro de `trace.trace_task()` en el orquestador) — candidato a mejora.

---

## Corrida 4 — Resultado verificable del caso de uso

### Predicción (dataset real, jul 2026)
```text
Argentina vs France        (neutral)
Argentina win: 47.7% | Draw: 22.8% | France win: 29.5%
Model: poisson_v2 | xG: Argentina 1.82 - 1.39 France
Elo: Argentina 2075.6 vs France 2015.72 | history_size: 49495
```

### Evaluación (últimos 300 partidos como test set)
```text
elo_baseline  -> brier 0.5479 | log_loss 0.9264 | rps 0.1770
poisson_v2    -> brier 0.5221 | log_loss 0.8903 | rps 0.1642   (gana en las 3)
```

### Qué se observa
Pipeline completo sin data leakage (features solo con historial previo a cada partido).
La primera versión (`poisson_v1`) perdía contra el baseline Elo; tras diagnosticar que
desaprovechaba el Elo e ignoraba la localía, se rediseñó (`poisson_v2`: supremacía Elo
log-lineal + localía), eligiendo parámetros sobre una ventana de validación y reportando
una sola vez sobre el test set no tocado. El modelo principal ahora **supera al baseline en
Brier, log loss y RPS**. Detalle en `cases/football_predictor/README.md`.
