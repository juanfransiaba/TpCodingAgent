import subprocess


def run_command(command: str) -> str:
    """Runs a terminal command and returns stdout, stderr and return code."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = ""

        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"

        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

        output += f"Return code: {result.returncode}"

        return output

    except subprocess.TimeoutExpired:
        return "Error: command took more than 30 seconds"
    except Exception as error:
        return f"Error running command: {error}"
