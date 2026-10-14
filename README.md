# SmartCodex

SmartCodex v1 routes a task to a Codex model using local rules or an optional AI classifier, then starts Codex CLI. It requires Python 3.10+ and Codex CLI available on `PATH`. The Python package has no runtime dependencies and does not require an OpenAI API key.

## Install from this repository

From the repository root, install the package into the active Python environment:

```powershell
py -m pip install .
smartcodex --help
```

For development, create and activate a virtual environment first:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install .
```

## PowerShell usage

Quote a prompt containing spaces. `--router rules` uses only local routing; `smart` is the default and invokes the AI classifier only when local rules are uncertain. `--router ai` always requests AI classification unless `--dry-run` is set.

```powershell
smartcodex "Ubah teks tombol Simpan menjadi Kirim"
smartcodex --router rules "Tambahkan validasi form"
smartcodex --router ai "Audit integrasi ini"
smartcodex --mode exec "Periksa konfigurasi proyek"
```

Preview a local routing decision without starting Codex or an AI classifier:

```powershell
smartcodex --dry-run "Ubah warna tombol login"
```

In `exec` and `loop` mode, Codex uses the `read-only` sandbox by default. Add `--write` to allow workspace edits. Chat mode retains the v1 `workspace-write` sandbox and `on-request` approval behavior. Legacy `--force-tier` values retain their original model mapping, including `sol-low` to Sol Low. Astra routing requires the explicit `--allow-astra` option.

## v1 limitations

- Routing sees only the prompt; it does not inspect the target repository.
- The interactive chat routes only its initial prompt. Follow-up messages remain in that Codex session and are not routed again.
- Loop mode starts a separate `codex exec` session for each prompt and does not preserve chat history.
- Model availability depends on the Codex account and CLI. AI routing uses Luna Low as the classifier and falls back to local rules on failure.
- This package does not include project analysis, planning, task scheduling, session management, or per-subtask routing.

The project testing configuration uses **GPT-6 Luna Low** as the default model. Manually selected legacy tiers continue to map to their v1 models.
