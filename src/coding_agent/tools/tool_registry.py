from coding_agent.tools.command_tool import run_command
from coding_agent.tools.file_tools import list_files, read_file, write_file
from coding_agent.tools.memory_tools import (
    memory_context,
    remember_command,
    remember_decision,
)
from coding_agent.tools.rag_search_tool import rag_search
from coding_agent.tools.repo_tools import search_code, tree_files, view_file
from coding_agent.tools.web_search_tool import web_search

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a file given its path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes content to a file, replacing its current content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Runs a terminal command and returns stdout and stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory to list.",
                    }
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches information on the web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tree_files",
            "description": "Returns a compact tree of files and folders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "The directory to inspect.",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum folder depth to include.",
                    },
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Searches a string in code and documentation files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The string to search for.",
                    },
                    "directory": {
                        "type": "string",
                        "description": "The directory to search in.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "Reads a whole file or a numbered line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to read.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional first line to include.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional last line to include.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Searches local RAG documentation and returns relevant chunks with sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The RAG query.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of chunks to return.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_decision",
            "description": "Stores an important project decision in persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Short decision topic.",
                    },
                    "decision": {
                        "type": "string",
                        "description": "Decision to remember.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this decision was made.",
                    },
                },
                "required": ["topic", "decision", "rationale"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_command",
            "description": "Stores a useful project command in persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command that is useful for this project.",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "When and why to use this command.",
                    },
                },
                "required": ["command", "purpose"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_context",
            "description": "Returns compact persistent memory for this project.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "list_files": list_files,
    "web_search": web_search,
    "tree_files": tree_files,
    "search_code": search_code,
    "view_file": view_file,
    "rag_search": rag_search,
    "remember_decision": remember_decision,
    "remember_command": remember_command,
    "memory_context": memory_context,
}

TOOLS_WITH_SUPERVISION = {
    "write_file",
    "run_command",
    "remember_decision",
    "remember_command",
}
