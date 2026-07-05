"""Genera evidencia de dos tareas del agente para la entrega del TP.

Corre el agente REAL (orquestador -> subagentes -> harness -> LLM + tools) sobre:

  Tarea A (memoria):    el agente recupera decisiones/comandos desde la memoria
                        persistente del proyecto.
  Tarea B (estrategia): el agente enfrenta un pedido sin evidencia disponible
                        (archivo inexistente) y debe detectarlo, cambiar de
                        estrategia o pedir ayuda en vez de inventar un fix.

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

TAREA_MEMORIA = (
    "Usando la memoria persistente del proyecto (llama a la tool memory_context), "
    "decime de donde sacamos el dataset de futbol y con que comando evaluamos los "
    "modelos. Aclara explicitamente que esa informacion viene de la memoria del proyecto."
)

TAREA_ESTRATEGIA = (
    "Arregla el bug del modulo de pagos en "
    "cases/football_predictor/src/football_predictor/payments.py que hace fallar "
    "las transacciones con tarjeta."
)


def seed_memory(storage_path: str) -> None:
    """Pre-carga una decision y un comando para que la Tarea A tenga que recordarlos."""

    memory = ProjectMemory(storage_path)
    memory.remember_decision(
        topic="dataset_futbol",
        decision=(
            "Usar el dataset martj42 'International football results 1872-2026' como "
            "cases/football_predictor/data/results.csv."
        ),
        rationale=(
            "Es la fuente citada en el SPEC, trae exactamente las columnas que espera "
            "data.py y permite calcular Elo, forma, goles y head-to-head sin scraping."
        ),
    )
    memory.remember_command(
        command="python cases/football_predictor/scripts/evaluate.py --max-eval 300",
        purpose=(
            "Comparar Poisson vs baseline Elo sobre los ultimos 300 partidos jugados "
            "sin recomputar todo el historico en cada corrida."
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
    print("TAREA A - MEMORIA PERSISTENTE")
    print("=" * 70)
    orchestrator.run_turn(TAREA_MEMORIA)

    print("\n" + "=" * 70)
    print("TAREA B - CAMBIO DE ESTRATEGIA / PEDIR AYUDA (sin evidencia)")
    print("=" * 70)
    orchestrator.run_turn(TAREA_ESTRATEGIA)

    print("\n" + "=" * 70)
    print("EVIDENCIA GENERADA")
    print("=" * 70)
    for task_id in newest_task_ids(2):
        print(f"- task_id: {task_id}")
        print(f"    runs/task_states/{task_id}.json")
        print(f"    runs/traces/{task_id}.json")
    print("Buscá estos task_id en el dashboard de Langfuse para las capturas.")


if __name__ == "__main__":
    main()
