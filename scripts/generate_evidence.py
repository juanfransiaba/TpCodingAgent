"""Genera evidencia de tareas del agente para la entrega del TP.

Caso de uso: AGREGAR UNA FUNCIONALIDAD a un proyecto existente. El repo objetivo
es un repositorio propio y separado (copia standalone de ChoppedApp, NestJS +
React), fuera del TP; su ruta esta en `workspace` de agent.config.yaml.

Corre el agente REAL (orquestador -> router/subagentes -> harness -> LLM + tools):

  Tarea A (RAG + feature): el agente agrega un endpoint GET /store/items/:id al
                           backend NestJS, apoyandose en el RAG del ecosistema
                           (controllers, providers, excepciones) y mostrando las
                           fuentes recuperadas.
  Tarea B (memoria):       el agente recupera desde la memoria persistente la
                           convencion de endpoints y el comando de tests.
  Tarea C (estrategia):    el agente enfrenta un pedido sin evidencia (archivo
                           inexistente) y debe detectarlo, cambiar de estrategia
                           o pedir ayuda en vez de inventar un fix.

Cada turno guarda:
  - runs/task_states/<task_id>.json
  - runs/traces/<task_id>.json
  - traza en Langfuse (si hay keys en .env)

Uso:
  PYTHONPATH=src python scripts/generate_evidence.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
os.chdir(REPO_ROOT)

from coding_agent.core.config import load_config
from coding_agent.runtime.orchestrator import CodingAgentOrchestrator
from coding_agent.memory.project_memory import ProjectMemory

TAREA_RAG_FEATURE = (
    "Agrega al backend NestJS un endpoint GET /store/items/:id que devuelva un "
    "unico item del catalogo por su id, y que responda 404 si el id no existe. "
    "Consulta primero el RAG del proyecto para seguir las convenciones de NestJS "
    "(controller, service y excepciones) y agrega un test unitario del service. "
    "Mostra que fuentes del RAG usaste."
)

TAREA_MEMORIA = (
    "Usando la memoria persistente del proyecto, decime que convencion seguimos "
    "para buscar un recurso por id que no existe y con que comando corremos los "
    "tests del backend. Aclara explicitamente que esa informacion viene de la "
    "memoria del proyecto."
)

TAREA_ESTRATEGIA = (
    "Arregla el bug del modulo de pagos en "
    "backend/src/payments/payments.service.ts que hace fallar los cobros con tarjeta."
)


def seed_memory(storage_path: str) -> None:
    """Pre-carga una decision y un comando para que la Tarea B tenga que recordarlos."""

    memory = ProjectMemory(storage_path)
    memory.remember_decision(
        topic="convencion_endpoints",
        decision=(
            "Para buscar un recurso por id, el service hace el lookup y lanza "
            "NotFoundException si no existe; el controller solo delega. Los mensajes "
            "de error van en espanol."
        ),
        rationale=(
            "Es el patron idiomatico de NestJS (StoreService.buy ya lanza "
            "NotFoundException('Item no encontrado')) y mantiene el status 404 "
            "consistente en todo el backend."
        ),
    )
    memory.remember_command(
        command="cd backend && npm test  # desde la raiz del repo objetivo",
        purpose=(
            "Corre los tests Jest (*.spec.ts) del backend NestJS para validar una "
            "feature nueva."
        ),
    )


def newest_task_ids(limit: int) -> list[str]:
    states_dir = REPO_ROOT / "runs" / "task_states"
    if not states_dir.exists():
        return []
    files = sorted(states_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return [path.stem for path in files[-limit:]]


def main() -> None:
    config = load_config(str(REPO_ROOT / "agent.config.yaml"))
    memory_path = config.get("memory", {}).get("path", "memory/project_memory.json")

    seed_memory(memory_path)

    orchestrator = CodingAgentOrchestrator(config)

    print("=" * 70)
    print("TAREA A - RAG + AGREGAR FEATURE (GET /store/items/:id)")
    print("=" * 70)
    orchestrator.run_turn(TAREA_RAG_FEATURE)

    print("\n" + "=" * 70)
    print("TAREA B - MEMORIA PERSISTENTE")
    print("=" * 70)
    orchestrator.run_turn(TAREA_MEMORIA)

    print("\n" + "=" * 70)
    print("TAREA C - CAMBIO DE ESTRATEGIA / PEDIR AYUDA (sin evidencia)")
    print("=" * 70)
    orchestrator.run_turn(TAREA_ESTRATEGIA)

    print("\n" + "=" * 70)
    print("EVIDENCIA GENERADA")
    print("=" * 70)
    for task_id in newest_task_ids(3):
        print(f"- task_id: {task_id}")
        print(f"    runs/task_states/{task_id}.json")
        print(f"    runs/traces/{task_id}.json")
    print("Busca estos task_id en el dashboard de Langfuse para las capturas.")


if __name__ == "__main__":
    main()
