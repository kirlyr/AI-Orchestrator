"""Read-only, bounded repository metadata analysis for SmartCodex."""
from __future__ import annotations

import json
import os
import re
import subprocess
try:  # Python 3.10 support without adding a runtime dependency.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {".git", ".venv", "venv", ".smartcodex", "node_modules", "vendor", "dist", "build", "__pycache__", ".next", "target", "coverage"}
SECRET_PARTS = {".env", "credentials", "credential", "secret", "secrets", "id_rsa", "id_ed25519", "private_key", "private-key"}
MANIFESTS = {"package.json", "composer.json", "pyproject.toml", "requirements.txt", "pipfile", "go.mod", "cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "gemfile", "mix.exs", "*.csproj"}
DEFAULT_MAX_PATHS = 5000
DEFAULT_MAX_CANDIDATES = 20
DEFAULT_MAX_FILE_BYTES = 64 * 1024
DEFAULT_MAX_TOTAL_BYTES = 256 * 1024


@dataclass(frozen=True)
class RepoFile:
    path: str
    size_bytes: int
    tracked: bool
    status: str = "clean"


@dataclass(frozen=True)
class RepoSummary:
    root: str
    is_git: bool
    branch: str | None
    files: tuple[RepoFile, ...]
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    candidates: tuple[str, ...]
    truncated: bool
    total_bytes: int
    warnings: tuple[str, ...] = ()


class RepoAnalysisError(RuntimeError):
    """Safe analyzer failure; messages never include file contents."""


def _safe_relative(root: Path, path: Path) -> str | None:
    try:
        resolved = path.resolve(strict=False)
        rel = resolved.relative_to(root)
    except (OSError, ValueError, RuntimeError):
        return None
    return rel.as_posix()


def _is_secret(path: Path) -> bool:
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    sensitive_names = ("credential", "secret", "private_key", "private-key", "id_rsa", "id_ed25519", "service-account", "service_account")
    return (name.startswith(".env") or any(part in SECRET_PARTS for part in parts)
            or any(term in name for term in sensitive_names)
            or any(x in name for x in (".pem", ".p12", ".pfx", ".key")))


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepoAnalysisError(f"Git command gagal ({type(exc).__name__}).") from None
    if result.returncode:
        raise RepoAnalysisError(f"Git command gagal (exit {result.returncode}).")
    return result.stdout


def _manifest_hints(path: Path) -> tuple[set[str], set[str]]:
    languages: set[str] = set()
    frameworks: set[str] = set()
    name = path.name.lower()
    try:
        if name == "package.json":
            data = json.loads(path.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            languages.add("JavaScript")
            if "typescript" in deps or path.parent.joinpath("tsconfig.json").exists(): languages.add("TypeScript")
            for dep, label in (("react", "React"), ("next", "Next.js"), ("vue", "Vue"), ("@angular/core", "Angular"), ("express", "Express"), ("svelte", "Svelte")):
                if dep in deps: frameworks.add(label)
        elif name == "composer.json":
            data = json.loads(path.read_text(encoding="utf-8")); languages.add("PHP")
            deps = {**data.get("require", {}), **data.get("require-dev", {})}
            for dep, label in (("laravel/framework", "Laravel"), ("symfony/framework-bundle", "Symfony")):
                if dep in deps: frameworks.add(label)
        elif name == "pyproject.toml":
            if tomllib is None:
                return languages, frameworks
            data = tomllib.loads(path.read_text(encoding="utf-8")); languages.add("Python")
            raw = str(data.get("project", {}).get("dependencies", [])) + str(data.get("tool", {}))
            for dep, label in (("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask")):
                if dep.lower() in raw.lower(): frameworks.add(label)
        elif name == "requirements.txt":
            languages.add("Python")
            text = path.read_text(encoding="utf-8", errors="replace")[:DEFAULT_MAX_FILE_BYTES].lower()
            for dep, label in (("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask")):
                if re.search(rf"(?m)^\s*{dep}(?:[<=>~!;\[]|\s|$)", text): frameworks.add(label)
        elif name == "go.mod": languages.add("Go")
        elif name == "cargo.toml": languages.add("Rust")
        elif name in {"pom.xml", "build.gradle", "build.gradle.kts"}: languages.add("Java")
        elif name == "gemfile": languages.add("Ruby")
        elif name == "mix.exs": languages.add("Elixir")
    except (OSError, ValueError, TypeError):
        pass
    return languages, frameworks


class RepoAnalyzer:
    """Analyze a repository without writing files or reading source file bodies."""
    def __init__(self, root: str | os.PathLike[str] = ".", *, max_paths: int = DEFAULT_MAX_PATHS,
                 max_candidates: int = DEFAULT_MAX_CANDIDATES, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
                 max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES):
        self.requested_root = Path(root).expanduser().resolve()
        self.max_paths = max(1, int(max_paths)); self.max_candidates = max(0, int(max_candidates))
        self.max_file_bytes = max(0, int(max_file_bytes)); self.max_total_bytes = max(0, int(max_total_bytes))

    def analyze(self, prompt: str = "") -> RepoSummary:
        if not self.requested_root.is_dir(): raise RepoAnalysisError("Project root bukan direktori yang dapat dibaca.")
        root = self.requested_root
        is_git = False; branch = None; warnings: list[str] = []; status_map: dict[str, str] = {}; tracked: set[str] = set()
        try:
            actual = Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
            # Analyze the requested directory, not an ancestor's broader contents.
            if actual != root:
                warnings.append("Direktori berada di dalam Git repository lain; memakai fallback lokal.")
            else:
                is_git = True
                branch = _git(root, "branch", "--show-current").strip() or None
                tracked.update(x for x in _git(root, "ls-files", "-z").split("\0") if x)
                records = iter(_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0"))
                for record in records:
                    if len(record) < 4: continue
                    status = record[:2]
                    rel = record[3:]
                    # With -z, rename/copy records are followed by the source path.
                    if "R" in status or "C" in status:
                        next(records, None)
                    status_map[rel] = status.strip() or "modified"
        except RepoAnalysisError as exc:
            warnings.append(str(exc))
            is_git = False

        entries: list[RepoFile] = []; languages: set[str] = set(); frameworks: set[str] = set(); truncated = False; total_bytes = 0
        # Walk without following symlink directories; each resolved file must remain under root.
        for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
            base_path = Path(base)
            dirs[:] = sorted(d for d in dirs if d.lower() not in IGNORED_DIRS and not (base_path / d).is_symlink())
            for filename in sorted(names):
                path = base_path / filename
                rel = _safe_relative(root, path)
                if rel is None or _is_secret(path) or path.is_symlink(): continue
                if any(part.lower() in IGNORED_DIRS for part in Path(rel).parts): continue
                if len(entries) >= self.max_paths: truncated = True; break
                try: size = path.stat().st_size
                except OSError: continue
                if size > self.max_file_bytes or total_bytes + size > self.max_total_bytes:
                    truncated = True
                    # retain tree metadata only within byte budget
                    continue
                total_bytes += size
                is_manifest = filename.lower() in MANIFESTS or filename.lower().endswith(".csproj")
                if is_manifest:
                    l, f = _manifest_hints(path); languages.update(l); frameworks.update(f)
                entries.append(RepoFile(rel, size, rel in tracked, status_map.get(rel, "clean")))
            if len(entries) >= self.max_paths: break
        if not is_git:
            # In fallback mode explicitly mark local files; no git metadata inferred.
            entries = [RepoFile(f.path, f.size_bytes, False, "local") for f in entries]
        candidates = self._rank_candidates(entries, prompt)
        return RepoSummary(str(root), is_git, branch, tuple(entries), tuple(sorted(languages)), tuple(sorted(frameworks)),
                           tuple(candidates), truncated, total_bytes, tuple(warnings))

    def _rank_candidates(self, files: list[RepoFile], prompt: str) -> list[str]:
        terms = {t.lower() for t in re.findall(r"[\w.-]{3,}", prompt) if t.lower() not in {"the", "and", "for", "with", "from", "ubah", "buat", "untuk"}}
        scored = []
        for entry in files:
            p = entry.path.lower(); basename = Path(p).name
            score = sum(4 for term in terms if term in p)
            if basename in {"readme.md", "pyproject.toml", "package.json", "composer.json"}: score += 1
            if entry.status != "clean": score += 1
            if score: scored.append((-score, p, entry.path))
        scored.sort()
        return [x[2] for x in scored[:self.max_candidates]]
