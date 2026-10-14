## Model Selection
- FAST: Simple and well-defined work -> fast_worker.
- STANDARD: Routine implementation -> standard_worker.
- DEEP: Complex reasoning -> deep_worker.
- CRITICAL: Report the need for stronger reasoning to the parent.
- The parent agent owns all escalation decisions.
- Do not escalate based on prompt length or file count alone.

## Execution
- Prefer completing simple tasks directly.
- Delegate only when a bounded independent task benefits from a separate worker.
- Do not delegate to a worker using the same model and effort unless there is a clear benefit.
- Avoid repeated repository exploration.
- Assign clear file ownership before parallel edits.
- Never overwrite another worker's uncommitted changes.
- Return concise findings, changed files, and test results.

## Escalation
- Escalate only after identifying a concrete blocker, failed validation, or reasoning limitation.
- Prefer FAST -> STANDARD -> DEEP when necessary.
- The parent decides whether escalation is justified.
- Allow at most one escalation per subtask by default.
- Do not retry the same failed approach without new evidence.
- Preserve findings when handing work to another worker.
- Do not start another agent solely to confirm an obvious result.
