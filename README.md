# Codex Smart Routing starter (project-level)

Place `AGENTS.md` and `.codex/` in the root of your repo. These define project instructions and three custom subagents. Codex's main model defaults to GPT-6.1 Sol Low for normal direct invocations.

Usage, from the project directory:

- `codex`: main = Sol Low (project config fallback)
- `codex -m gpt-6-luna -c model_reasoning_effort=low "Ubah label tombol login"`: main = Luna Low
- `codex -m gpt-6.1-sol -c model_reasoning_effort=medium "Cari dan perbaiki bug integrasi login"`: main = Sol Medium

`AGENTS.md` can encourage delegation to agents with their own models, but cannot automatically change the model of the main interactive chat per follow-up message.

For classification *before* each new task, use a launcher command such as `smartcodex` to pick `-m` and `-c` values, then invoke Codex. The earlier Smart Codex Launcher prototype routes only the first prompt of an interactive session and is not yet fully project-aware.

If you want per-turn model switching *while preserving the same conversation*, a custom frontend/controller using a supported Codex API (e.g. app server/SDK) is a distinct advanced integration. Validate model availability on your ChatGPT account.

To keep config local rather than commit it, put `/AGENTS.md` and `/.codex/` into `.git/info/exclude` (recommended for personal-only files) or your repo's `.gitignore`.
