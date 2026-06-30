from pathlib import Path

from coding_agent.agents.main_agent import prepare_task
from coding_agent.core.config import load_config
from coding_agent.core.harness import run_agent_turn
from coding_agent.core.llm_client import MODEL
from coding_agent.core.planner import get_plan
from coding_agent.core.task_state import TaskState
from coding_agent.memory.project_memory import ProjectMemory
from coding_agent.observability.tracing import TraceRecorder
from coding_agent.prompts.system_prompt import SYSTEM_PROMPT


def chat() -> None:
    config = load_config()
    memory = ProjectMemory(config.get("memory", {}).get("path", "memory/project_memory.json"))

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    turn = 0
    total_iterations = 0
    plan_mode = False
    supervision = False

    print("Coding agent ready.")
    print("Commands: /plan, /supervision, /exit")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "/exit":
            print(f"\nFinished. {turn} turns, {total_iterations} total iterations.")
            break

        if user_input.lower() == "/plan":
            plan_mode = not plan_mode
            status = "ON" if plan_mode else "OFF"
            print(f"Plan mode: {status}")
            continue

        if user_input.lower() == "/supervision":
            supervision = not supervision
            status = "ON" if supervision else "OFF"
            print(f"Supervision: {status}")
            continue

        messages.append({"role": "user", "content": user_input})
        task_state = TaskState(original_request=user_input)
        task_state.add_progress("User request received.")
        turn += 1

        print(f"\n{'-' * 50}")

        if plan_mode:
            print("Generating plan...")
            plan = get_plan(messages[:-1], user_input)
            print(f"\nPlan:\n{plan}\n")

            approval = input("Approve plan? [s/n]: ").strip().lower()

            if approval not in ("s", "si", "y", "yes"):
                print("Plan rejected. Task cancelled.")
                messages.pop()
                turn -= 1
                continue

            print("Plan approved. Executing...\n")

        trace = TraceRecorder(task_state=task_state, model=MODEL, config=config)

        with trace.trace_task():
            coordination_content = prepare_task(task_state, config, memory=memory)
            coordination_message = {
                "role": "system",
                "content": coordination_content,
            }
            messages.insert(
                len(messages) - 1,
                coordination_message,
            )
            trace.record_event(
                "coordination_brief",
                metadata={"content": coordination_content},
            )

            response, iterations = run_agent_turn(
                messages=messages,
                config=config,
                supervision=supervision,
                task_state=task_state,
                trace=trace,
            )

            total_iterations += iterations
            task_state.mark_completed(response)
            memory.record_task_state(task_state)
            trace.record_final(task_state)
            state_path = task_state.save_json(
                Path("runs") / "task_states" / f"{task_state.task_id}.json"
            )
            trace_path = trace.save_local_trace()
            trace.flush()

            messages.remove(coordination_message)

        print(f"\nAgent: {response}")
        print(f"Iterations this turn: {iterations}")
        print(f"Task state saved to: {state_path}")
        print(f"Project memory saved to: {memory.storage_path}")
        print(f"Trace saved to: {trace_path}")


if __name__ == "__main__":
    chat()
