"""Prompt registry (ai-reliability T1.4): every static system-prompt template lives as a
frontmatter-tagged ``.md`` file under ``erp/assistant/prompts/`` instead of an inline string
constant, so prompts are diffable, versioned artifacts — and every AI call can record exactly
which prompt version produced it via ``Prompt.ref``.

Frontmatter is deliberately not YAML (no new dependency): three fields only — ``id``, ``version``
(semver), ``changelog`` (a list of ``  - "..."`` lines). The body after the closing ``---`` is the
prompt template verbatim, placeholders and all — moved here unchanged from its old inline literal.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptNotFoundError(KeyError):
    """Raised by ``get()`` for an id with no matching prompt file."""


class PromptRenderError(ValueError):
    """Raised by ``Prompt.render()`` when a template placeholder isn't supplied — fail loud
    rather than ship a half-rendered prompt to a model."""


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    changelog: tuple[str, ...]
    template: str
    ref: str

    def render(self, **kwargs) -> str:
        try:
            return self.template.format(**kwargs)
        except KeyError as exc:
            raise PromptRenderError(
                f"prompt {self.id!r} render is missing placeholder {exc}"
            ) from exc


def _parse_frontmatter(raw: str, path: Path) -> tuple[dict, list[str], str]:
    if not raw.startswith("---\n"):
        raise ValueError(f"prompt file {path.name} is missing its frontmatter header")
    _, _, rest = raw.partition("---\n")
    fm_text, sep, body = rest.partition("\n---\n")
    if not sep:
        raise ValueError(f"prompt file {path.name} frontmatter is never closed")
    meta: dict = {}
    changelog: list[str] = []
    for line in fm_text.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            changelog.append(line[len("  - "):].strip().strip('"'))
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, changelog, body.lstrip("\n")


def _load(path: Path) -> Prompt:
    meta, changelog, template = _parse_frontmatter(path.read_text(encoding="utf-8"), path)
    prompt_id = meta.get("id") or path.stem
    version = meta.get("version") or "0.0.0"
    sha = hashlib.sha256(template.encode("utf-8")).hexdigest()[:8]
    return Prompt(id=prompt_id, version=version, changelog=tuple(changelog),
                 template=template, ref=f"{prompt_id}@{version}#{sha}")


def _load_all() -> dict[str, Prompt]:
    return {p.id: p for p in (_load(path) for path in sorted(PROMPTS_DIR.glob("*.md")))}


# Loaded once, at import — every call site shares the same Prompt objects (stable ``.ref``).
_REGISTRY: dict[str, Prompt] = _load_all()


def get(prompt_id: str) -> Prompt:
    try:
        return _REGISTRY[prompt_id]
    except KeyError:
        raise PromptNotFoundError(f"unknown prompt id: {prompt_id!r}") from None
