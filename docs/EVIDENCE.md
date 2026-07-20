# Evidencias de corridas (TP Coding Agent Avanzado)

Caso de uso: **agregar una funcionalidad** al backend NestJS de `choppedapp_copia`
(repo propio externo, copia de ChoppedApp). Todas las corridas generan traza local
en `runs/traces/<task_id>.json` y estado en `runs/task_states/<task_id>.json`.

> **Cómo reproducir todo:** `PYTHONPATH=src python scripts/generate_evidence.py`
> (corre las 3 tareas de abajo y deja los `task_id` en `runs/`). Después completar
> los `task_id` reales en las secciones que dicen `<task_id: ...>`.

> **Langfuse:** las trazas suben al proyecto (región **US**,
> `https://us.cloud.langfuse.com`) además de guardarse localmente. Buscar en el
> dashboard por nombre `coding-agent-task` (el `task_id` va en el metadata).
>
> Config correcta en `.env` (el SDK v3 lee `LANGFUSE_HOST`, **no** `LANGFUSE_BASE_URL`):
> ```env
> LANGFUSE_PUBLIC_KEY=pk-lf-...
> LANGFUSE_SECRET_KEY=sk-lf-...
> LANGFUSE_HOST=https://us.cloud.langfuse.com
> ```

---

## Corrida 1 — RAG + agregar la feature (Tarea A)

- **task_id:** `d791ea4ec4c44190b110c03bcbf15dcc`

### Prompt usado
```text
Agrega al backend NestJS un endpoint GET /store/items/:id que devuelva un unico
item del catalogo por su id, y que responda 404 si el id no existe. Consulta primero
el RAG del proyecto para seguir las convenciones de NestJS (controller, service y
excepciones) y agrega un test unitario del service. Mostra que fuentes del RAG usaste.
```

### Capacidades observadas
- **RAG (Researcher, RAG-first):** recupera chunks del índice local
  `storage/vector_store/index.json` (5 docs / 15 chunks del ecosistema NestJS/TS).
- **Fuentes esperadas** (por relevancia): `rag_docs/nestjs_controllers.md`,
  `rag_docs/nestjs_exceptions_validation.md`, `rag_docs/nestjs_providers_di.md`,
  `rag_docs/nestjs_testing_jest.md`.
- **Implementer:** crea `getItem(id)` en `store.service.ts`, la ruta
  `@Get('items/:id')` en `store.controller.ts` y un `store.service.spec.ts`.
- **Tester:** corre `npm test` (solo si el Implementer hizo un `write_file` exitoso).
- **Reviewer:** decide `approved` / `changes_requested` / `blocked`.

### Qué se observa
El Researcher prioriza el RAG local (política RAG-first aplicada por runtime: `web_search`
se bloquea hasta que el subagente intentó `search_rag`), cita las fuentes, y recién
entonces el Implementer escribe siguiendo la convención del repo (lanzar
`NotFoundException`, no devolver `null`).

---

## Corrida 2 — Uso de memoria persistente (Tarea B)

- **task_id:** `9fc26c5514b04be3b6bd519faaa778bc`

### Prompt usado
```text
Usando la memoria persistente del proyecto, decime que convencion seguimos para
buscar un recurso por id que no existe y con que comando corremos los tests del
backend. Aclara explicitamente que esa informacion viene de la memoria del proyecto.
```

### Output esperado (de la memoria sembrada por `generate_evidence.py`)
```text
Esta información proviene de la memoria persistente del proyecto:
- Convención (semantic memory · convencion_endpoints): el service hace el lookup y
  lanza NotFoundException si no existe; el controller solo delega. Mensajes en español.
- Comando de tests (procedural memory): cd backend && npm test
```

### Qué se observa
El agente lee la memoria semántica (decisión `convencion_endpoints`) y procedural
(comando de tests) y las cita, distinguiendo que provienen de la memoria del proyecto
y no de inferencia propia.

---

## Corrida 3 — Cambio de estrategia / pedir ayuda (Tarea C)

- **task_id:** `dfdedb0eeace48dbbe4bf620459c1f9b`

### Prompt usado
```text
Arregla el bug del modulo de pagos en
backend/src/payments/payments.service.ts que hace fallar los cobros con tarjeta.
```

### Output esperado
```text
No puedo localizar backend/src/payments/payments.service.ts: el módulo payments no
existe en el backend (los módulos reales son users, auth, workouts, store, ...). No
tengo evidencia suficiente para aplicar un fix. ¿Me confirmás la ruta real?
```

### Qué se observa
El pedido no tiene evidencia real (el módulo `payments` no existe; el cobro real vive
en `store.service.ts` con puntos, no con tarjeta). El Implementer no escribe sin
evidencia, el Tester se saltea (no hubo `write_file`) y queda registrada la observación;
el agente **pide ayuda** en lugar de inventar un fix.

---

## Nota sobre determinismo

El comportamiento del LLM es no-determinista: los `task_id`, el número de iteraciones
y el texto exacto varían entre corridas. Lo que se mantiene es la **capacidad
observada** en cada tarea (RAG con fuentes, memoria citada, falta de evidencia →
pedir ayuda). Para las capturas del entregable 7, abrir en Langfuse cualquiera de las
3 trazas `coding-agent-task` generadas.
