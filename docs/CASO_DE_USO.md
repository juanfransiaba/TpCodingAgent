# Caso de uso — Agregar una funcionalidad a ChoppedApp

## Repositorio objetivo

El caso de uso (tipo de la consigna: *agregar una funcionalidad a un proyecto
existente*) opera sobre un **repositorio propio y separado**: `choppedapp_copia`,
una **copia standalone** de ChoppedApp (una app real de gimnasio/entrenamiento).

- **No es el ChoppedApp original.** Es una copia con su propio git y su propio
  repositorio en GitHub, para no tocar el original con este trabajo.
- **No vive dentro del repo del TP.** El agente lo modifica como repo externo, vía
  el `workspace` configurado en `agent.config.yaml`:

  ```yaml
  workspace: /Users/thiagoserebrinsky/facultad/projects/copiaDeChoppedApp/choppedapp_copia
  ```

- **Repo GitHub:** https://github.com/ThiagoSere/choppedapp_copia
  (clon local en `~/facultad/projects/copiaDeChoppedApp/choppedapp_copia`).

Stack del repo objetivo:

- **Backend:** NestJS 11 + TypeScript + TypeORM (Postgres). Tests con Jest.
- **Frontend:** React.
- **Módulos del backend:** `users`, `auth`, `workouts`, `exercises`,
  `training-session`, `achievements`, `gyms`, `store`, `scheduler`.

Ecosistema técnico del agente para este caso: **NestJS / TypeScript** (ver la base
RAG en `rag_docs/`).

## Objetivo concreto

Que el agente **agregue una funcionalidad concreta** al backend NestJS siguiendo
las convenciones del proyecto, apoyándose en el RAG del ecosistema y dejando el
cambio validado.

Funcionalidad de referencia usada en la evidencia:

> **`GET /store/items/:id`** — devolver un único ítem del catálogo de la tienda por
> su id, respondiendo **404** (`NotFoundException`) si el id no existe, con su
> **test unitario** del service.

Es un cambio acotado y verificable que reutiliza patrones ya presentes en el repo
(`StoreService.buy` ya lanza `NotFoundException('Item no encontrado')`).

## Criterio de "cumplido" (verificable)

1. En el repo objetivo existe el método `getItem(id)` en `store.service.ts` (devuelve
   el ítem o lanza `NotFoundException`), y la ruta `@Get('items/:id')` en
   `store.controller.ts`.
2. Hay un test (`store.service.spec.ts`) con un caso feliz y un caso de error, y
   `npm test` (desde `backend/`) pasa en verde.
3. El agente muestra **qué fuentes del RAG** usó para respetar las convenciones de
   NestJS (controllers, providers, excepciones).

## Cómo se prueba (3 tareas, cubren lo que pide la consigna)

Reproducibles con `PYTHONPATH=src python scripts/generate_evidence.py`:

| Tarea | Capacidad que demuestra |
| --- | --- |
| A. Agregar `GET /store/items/:id` | RAG + mostrar fuentes + implementación real |
| B. "¿Qué convención y con qué comando testeamos?" | Memoria persistente del proyecto |
| C. "Arreglá `payments.service.ts`" (no existe) | Detectar falta de evidencia, cambiar de estrategia / pedir ayuda |

El detalle de cada corrida (output, fuentes, `task_id` de Langfuse) se documenta en
[`EVIDENCE.md`](EVIDENCE.md).
