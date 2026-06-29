from coding_agent.core.config import load_config
from coding_agent.core.harness import run_agent_turn
from coding_agent.core.planner import get_plan

SYSTEM_PROMPT = """
You are a coding agent. Your job is to help with programming tasks by using tools.

Rules:
- Use tools when you need to inspect files, modify code, run commands, or search information.
- Do not claim that you changed files unless you actually used write_file.
- Do not claim that tests passed unless you actually used run_command.
- Respect the configured workspace and security policies.
- If you do not have enough evidence, explain what is missing and ask for help.
"""


def chat() -> None:
    config = load_config()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    turn = 0
    total_iterations = 0
    plan_mode = False
    supervision = False

    print("🤖 Coding agent ready.")
    print("Commands: /plan, /supervision, /exit")
    print("-" * 50)

    while True:
        user_input = input("\n👤 You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "/exit":
            print(f"\n👋 Finished. {turn} turns, {total_iterations} total iterations.")
            break

        if user_input.lower() == "/plan":
            plan_mode = not plan_mode
            status = "ON ✅" if plan_mode else "OFF ❌"
            print(f"📋 Plan mode: {status}")
            continue

        if user_input.lower() == "/supervision":
            supervision = not supervision
            status = "ON ✅" if supervision else "OFF ❌"
            print(f"👁️  Supervision: {status}")
            continue

        messages.append({"role": "user", "content": user_input})
        turn += 1

        print(f"\n{'─' * 50}")

        if plan_mode:
            print("📋 Generating plan...")
            plan = get_plan(messages[:-1], user_input)
            print(f"\n📋 Plan:\n{plan}\n")

            approval = input("Approve plan? [s/n]: ").strip().lower()

            if approval not in ("s", "si", "sí", "y", "yes"):
                print("❌ Plan rejected. Task cancelled.")
                messages.pop()
                turn -= 1
                continue

            print("✅ Plan approved. Executing...\n")

        response, iterations = run_agent_turn(
            messages=messages,
            config=config,
            supervision=supervision,
        )

        total_iterations += iterations

        print(f"\n🤖 Agent: {response}")
        print(f"📊 Iterations this turn: {iterations}")


if __name__ == "__main__":
    chat()
