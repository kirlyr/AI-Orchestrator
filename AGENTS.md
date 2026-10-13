# Intelligent Task Orchestration

## Objective
Minimize model usage while preserving code quality.

## Task Understanding
- Understand the user's goal and relevant project context.
- Do not assume a long prompt is a difficult task.
- Assess complexity based on dependencies, risks,
  reasoning requirements, and affected modules.
- Inspect only relevant project files.

## Task Decomposition
- Complete small tasks directly without subagents.
- For compound tasks, identify bounded subtasks.
- Avoid unnecessary task decomposition.
- Reuse existing project context and findings.


## Model Selection
- FAST: Simple and well-defined work -> fast_worker.
- STANDARD: Routine implementation -> standard_worker.
- DEEP: Complex reasoning -> deep_worker.
- CRITICAL: Escalate only when necessary.

## Execution
- Prefer the least expensive capable worker.
- Do not spawn agents merely because they exist.
- Avoid duplicated repository exploration.
- Keep implementation coordinated to prevent conflicts.
- Return concise findings to the main agent.

## Escalation
- Validate the results of each meaningful change.
- If a worker cannot solve a task reliably,
  reassess and delegate to a stronger worker.
- Do not repeatedly retry the same failed approach.
- Never escalate merely because the prompt is long.

## Safety
- Do not modify production data without approval.
- Run relevant tests after changes.
- Report failures and unresolved risks.