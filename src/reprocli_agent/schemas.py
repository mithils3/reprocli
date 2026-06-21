from __future__ import annotations

_BASH_CONTAINER = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a shell command in the sandbox working directory. "
            "Use for host inspection, git clone, apptainer exec (with uv for "
            "dependency installs), sbatch, and monitoring SLURM jobs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run."},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 3600).",
                },
            },
            "required": ["command"],
        },
    },
}

_BASH_CONDA = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a shell command in the sandbox working directory. "
            "Pass conda_env to run inside a specific conda environment — "
            "activation persists across calls via 'conda run'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run."},
                "conda_env": {
                    "type": "string",
                    "description": "Conda env name to run inside (create first with create_conda_env).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 3600).",
                },
            },
            "required": ["command"],
        },
    },
}

_CREATE_CONDA_ENV = {
    "type": "function",
    "function": {
        "name": "create_conda_env",
        "description": (
            "Create a new conda environment with a specific Python version. "
            "Call once during setup, then use conda_env=<name> in all bash calls."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Environment name, e.g. 'repro'.",
                },
                "python_version": {
                    "type": "string",
                    "description": "Python version, e.g. '3.10'.",
                },
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional conda packages to install alongside Python.",
                },
            },
            "required": ["name", "python_version"],
        },
    },
}

_LIST_FILES = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": (
            "List the file tree of a directory in the sandbox working directory. "
            "Use after git clone to find scripts, configs, and entry points."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path (default '.' = workdir root).",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Max depth (default 4).",
                },
                "max_entries": {
                    "type": "integer",
                    "description": "Max entries (default 300).",
                },
            },
            "required": [],
        },
    },
}

_READ_FILE = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file from the sandbox working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside workdir.",
                },
                "max_chars": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
}

_WRITE_FILE = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file in the sandbox working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside workdir.",
                },
                "content": {"type": "string", "description": "Text content to write."},
            },
            "required": ["path", "content"],
        },
    },
}

_FETCH_URL = {
    "type": "function",
    "function": {
        "name": "fetch_url",
        "description": "Fetch a public HTTP/HTTPS URL and return its text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP or HTTPS URL."},
                "max_chars": {"type": "integer"},
            },
            "required": ["url"],
        },
    },
}

_GITHUB_BROWSE = {
    "type": "function",
    "function": {
        "name": "github_browse",
        "description": "Browse a GitHub repository — README by default, or a specific file/directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "owner/repo or full GitHub URL.",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path (omit for README).",
                },
                "ref": {"type": "string", "description": "Branch, tag, or commit SHA."},
            },
            "required": ["repo"],
        },
    },
}

_HF_BROWSE = {
    "type": "function",
    "function": {
        "name": "hf_browse",
        "description": "Browse a HuggingFace model or dataset: card metadata and file listing.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "namespace/name or full HF URL.",
                },
                "repo_type": {"type": "string", "enum": ["model", "dataset"]},
            },
            "required": ["repo"],
        },
    },
}

_SHARED = [_LIST_FILES, _READ_FILE, _WRITE_FILE, _FETCH_URL, _GITHUB_BROWSE, _HF_BROWSE]

TOOL_SCHEMAS_CONTAINER: list[dict] = [_BASH_CONTAINER, *_SHARED]
TOOL_SCHEMAS_CONDA: list[dict] = [_BASH_CONDA, _CREATE_CONDA_ENV, *_SHARED]


def get_tool_schemas(use_container: bool) -> list[dict]:
    return TOOL_SCHEMAS_CONTAINER if use_container else TOOL_SCHEMAS_CONDA


def filter_schemas(schemas: list[dict], allowed: list[str]) -> list[dict]:
    """Return only the schemas whose function name is in the allowed list."""
    allowed_set = set(allowed)
    return [s for s in schemas if s["function"]["name"] in allowed_set]
