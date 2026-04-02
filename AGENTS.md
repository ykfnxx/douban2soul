# AGENTS.md — Douban2Soul Development Guidelines

## Project Overview

Douban2Soul is a personality profiling tool that analyzes Douban movie viewing records using LLMs.
This document defines the development conventions and constraints for all contributors (human and AI agents).

## Language

- **Code**: All code, comments, docstrings, variable names, and log/print messages must be in English.
- **LLM Prompts**: Prompts sent to LLMs should be in English. When analyzing Chinese content, instruct the LLM to read Chinese input but produce English output.
- **Documentation**: All docs under `docs/` and the primary `README.md` must be in English. A Chinese translation may be maintained as `README_ZH.md`.
- **Git**: Commit messages, branch names, and PR descriptions must be in English.

## Project Structure

```
Douban2Soul/
├── main.py                  # CLI entry point
├── scripts/
│   ├── llm_client.py        # Unified LLM client interface
│   ├── analysis_engine.py   # Layered analysis engine (L1-L4)
│   └── metadata_fetcher.py  # Movie metadata fetcher
├── docs/                    # Project documentation
├── output/                  # Generated reports (git-ignored)
├── cache/                   # Metadata cache (git-ignored)
├── AGENTS.md                # This file
├── README.md                # English README
└── README_ZH.md             # Chinese README
```

## Tech Stack

- **Python**: >= 3.10
- **Package Manager**: UV (use `uv sync` to install, `uv run` to execute)
- **LLM Providers**: Moonshot (recommended), OpenAI, DashScope, DeepSeek
- **Linting**: Ruff (configured in pyproject.toml)
- **Formatting**: Black (line-length=100)
- **Type Checking**: mypy

## Git Conventions

### Branching
- `main` is the primary branch. Keep it stable.
- Use feature branches for development: `feat/<short-description>`
- Use fix branches for bug fixes: `fix/<short-description>`
- Branch names must be lowercase, hyphen-separated.

### Commits
- Write clear, concise commit messages.
- Format: `<type>: <short description>`
- Types: `init`, `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Example: `feat: add genre-based L3 analysis`
- Keep commits atomic — one logical change per commit.

### Pull Requests
- Require at least one review before merging.
- Squash-merge feature branches into `main`.
- Delete the branch after merge.

## Code Style

### General
- Follow PEP 8 with line length of 100.
- Use type hints for function signatures.
- Keep functions focused — one function, one responsibility.
- Prefer clear names over comments. Add comments only when the "why" isn't obvious.

### Naming
- Classes: `PascalCase` (e.g., `DoubanAnalyzer`)
- Functions/methods: `snake_case` (e.g., `generate_l1_base_stats`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PROVIDER`)
- Private members: prefix with `_` (e.g., `_save_report`)

### Error Handling
- Raise specific exceptions with clear messages.
- Fail fast — validate inputs early.
- Use `ValueError` for invalid arguments, `RuntimeError` for operational failures.

### File I/O
- Always specify `encoding='utf-8'` when reading/writing files.
- Use `pathlib.Path` instead of `os.path`.

## Dependencies

- All dependencies must be declared in `pyproject.toml`.
- Pin minimum versions (e.g., `openai>=1.0.0`).
- Do not add dependencies without justification.
- Dev dependencies go in `[project.optional-dependencies] dev`.

## What NOT to Commit

These are enforced by `.gitignore`:
- User data files (`*.json` except package manifests)
- `cache/` directory
- `output/` directory
- Virtual environments (`.venv/`, `venv/`)
- Environment variable files (`.env`)
- IDE configurations (`.vscode/`, `.idea/`)
- OS artifacts (`.DS_Store`)

## Testing

- Tests go in `tests/` directory.
- Test files: `test_*.py`
- Use `pytest` as the test runner: `uv run pytest`
- Write tests for new features and bug fixes.

## Agent Collaboration

- **Claim before you work**: Always claim a task before starting. If the claim fails, move on.
- **No duplicate work**: Check if someone else is already working on a task.
- **Review required**: Code changes must be reviewed by at least one other agent or human before merging.
- **Report progress**: Post brief updates in the task thread.
- **Ask when blocked**: If requirements are unclear, ask @SolidYang for clarification.
