"""Auto-gera INDEX.md walking tree + lendo YAML frontmatter dos READMEs.

Uso:
    python scripts/index.py            # gera INDEX.md na raiz
    python scripts/index.py --check    # verifica sem escrever

Frontmatter esperado (opcional, mas recomendado em READMEs ativos):
    ---
    title: <titulo>
    type: clean-experiment | dirty-lab | sub-experiment | report
    status: active | closed | superseded | archived | empirical-coverage-complete
    tags: [tcf, delta-aware, ...]
    created: YYYY-MM-DD
    updated: YYYY-MM-DD
    ---

NAO usa libs externas (sem PyYAML). Parse manual simples.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Onde procurar READMEs
SCAN_PATHS = [
    ROOT / "experiments" / "lab" / "clean",
    ROOT / "experiments" / "lab" / "dirty",
    ROOT / "docs",
    ROOT / "scripts",
]

# Skip these (historic / archived)
SKIP_PARTS = {"old", "_archive", "archive", "__pycache__"}


def parse_frontmatter(text: str) -> dict | None:
    """Extrai YAML frontmatter de um arquivo .md. Retorna dict ou None.

    Frontmatter esperado: bloco entre `---` no inicio do arquivo.
    Parse simples — suporta apenas `key: value` e `key:` seguido de
    lista `- item` ou `[a, b]`.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    out: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("#"):
            i += 1
            continue
        m = re.match(r"^([a-zA-Z_][\w-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            # Lista? olha proxima linha
            items = []
            j = i + 1
            while j < len(lines) and lines[j].startswith("  -"):
                items.append(lines[j][3:].strip())
                j += 1
            out[key] = items
            i = j
        elif value.startswith("[") and value.endswith("]"):
            out[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
            i += 1
        else:
            out[key] = value
            i += 1
    return out


def scan_readmes() -> list[dict]:
    """Walk SCAN_PATHS, retorna lista de entries com frontmatter."""
    entries: list[dict] = []
    for scan_path in SCAN_PATHS:
        if not scan_path.exists():
            continue
        for readme in scan_path.rglob("README.md"):
            parts = set(readme.parts)
            if parts & SKIP_PARTS:
                continue
            text = readme.read_text(encoding="utf-8", errors="ignore")
            fm = parse_frontmatter(text)
            rel = readme.relative_to(ROOT).as_posix()
            entry = {
                "path": rel,
                "dir": str(Path(rel).parent),
                "frontmatter": fm,
            }
            entries.append(entry)
    return entries


def render_index(entries: list[dict]) -> str:
    """Gera markdown do INDEX.md."""
    out = [
        "# INDEX — auto-gerado por `scripts/index.py`",
        "",
        f"Total READMEs com frontmatter: "
        f"{sum(1 for e in entries if e['frontmatter'])}",
        f"Total READMEs sem frontmatter: "
        f"{sum(1 for e in entries if not e['frontmatter'])}",
        "",
        "> Para adicionar entrada nova: adicionar YAML frontmatter no README e re-rodar.",
        "",
    ]

    # Agrupar por type
    by_type: dict[str, list[dict]] = {}
    no_fm: list[dict] = []
    for e in entries:
        if not e["frontmatter"]:
            no_fm.append(e)
            continue
        t = e["frontmatter"].get("type", "untyped")
        by_type.setdefault(t, []).append(e)

    for t in sorted(by_type.keys()):
        out.append(f"## Type: `{t}`")
        out.append("")
        out.append("| Path | Title | Status | Tags | Updated |")
        out.append("|---|---|---|---|---|")
        for e in sorted(by_type[t], key=lambda x: x["path"]):
            fm = e["frontmatter"]
            title = fm.get("title", "(sem title)")
            status = fm.get("status", "?")
            tags = fm.get("tags", [])
            if isinstance(tags, list):
                tags_str = ", ".join(tags[:4])
            else:
                tags_str = str(tags)
            updated = fm.get("updated", "?")
            out.append(
                f"| [{e['dir']}](./{e['path']}) | {title} | {status} | "
                f"{tags_str} | {updated} |"
            )
        out.append("")

    if no_fm:
        out.append("## READMEs sem frontmatter (candidatos a adicionar)")
        out.append("")
        for e in sorted(no_fm, key=lambda x: x["path"])[:50]:
            out.append(f"- `{e['path']}`")
        if len(no_fm) > 50:
            out.append(f"- ... (+{len(no_fm) - 50} mais)")
        out.append("")

    out.append("---")
    out.append("")
    out.append("Re-gere com: `python scripts/index.py`")
    out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="apenas verificar (nao escreve)")
    args = parser.parse_args()

    entries = scan_readmes()
    md = render_index(entries)

    target = ROOT / "INDEX.md"
    if args.check:
        print(md)
        print(f"\n(--check: nao escreveu em {target})")
    else:
        target.write_bytes(md.encode("utf-8"))
        print(f"Escrito: {target}")
        print(f"  entries: {len(entries)}")
        print(f"  com frontmatter: {sum(1 for e in entries if e['frontmatter'])}")


if __name__ == "__main__":
    main()
