"""Repro toolset.

Phase 2 ships the workspace-scoped tools the agent acts through: a cwd-confined
shell (``workspace_bash``) and confined file ops (``read_file`` / ``write_file``
/ ``apply_patch``). Phase 4 adds the metered ``run_gpu`` tool and assembles
``REPRO_TOOLS`` + handler dispatch here, wired into ``loop.py`` via
``dispatch.execute_repro_tool_call``.
"""
