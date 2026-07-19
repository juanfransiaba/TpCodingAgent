# Next Steps

Este documento resume lo que falta para cerrar la entrega.

## Estado Actual

Ya esta funcionando:

- agente modular con orquestador, router de subagentes y harness propio;
- subagentes con tools propias por rol (ver `agents/specs.py`);
- RAG local (NestJS/TypeScript) con ingesta y retrieval;
- politica RAG-first aplicada por runtime;
- memoria persistente;
- observabilidad local y Langfuse;
- tests unitarios;
- caso de uso sobre un repo propio y externo `choppedapp_copia` (copia de ChoppedApp).

## Prioridad Alta

### 1. Correr las 3 tareas de evidencia

```bash
export PYTHONPATH=src
python scripts/generate_evidence.py
```

Genera las corridas de las tareas A (RAG + feature), B (memoria) y C (cambio de
estrategia), con estado en `runs/task_states/` y trazas en `runs/traces/` + Langfuse.

### 2. Capturas de Langfuse

Capturar al menos una traza completa (nombre `coding-agent-task`) donde se vea:
prompt, modelo, tool calls, RAG docs recuperados, memoria, iteraciones, latencia,
tokens/costo y resultado final. Completar los `task_id` reales en `docs/EVIDENCE.md`.

### 3. Validar la feature en el repo objetivo

Si la Tarea A implementó `GET /store/items/:id`, correr los tests del backend:

```bash
cd backend   # dentro del repo objetivo choppedapp_copia
npm install   # una vez
npm test
```

## Prioridad Media

### 4. Tests adicionales del agente

- `CodingAgentOrchestrator`;
- manejo de errores en observabilidad;
- permisos de commands con mas casos borde.

## Prioridad Baja

- Ampliar el RAG de NestJS (guards/JWT, DTOs con `class-validator`, TypeORM avanzado).
- Mejorar autodescubrimiento de tools estilo plugin (extra opcional de la consigna).
- Refinar costos estimados si se cambia de modelo.
