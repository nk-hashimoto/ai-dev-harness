#!/usr/bin/env python3
"""ai-dev-harness のインストーラ。

shared/(ツール共通)と adapters/(ツール別)の原本から、各ツールの置き場所と書式へ組み立てて配置する。
既存のファイルは --force を付けない限り上書きしない(上書きは取り消せないため、既定を安全側に倒す)。

    python3 scripts/install.py --tool kiro --home                      # 規範・入口・スキルをユーザー単位へ
    python3 scripts/install.py --tool kiro --project ~/src/app         # role 定義・雛形をプロジェクトへ
    python3 scripts/install.py --tool codex --home --project . --dry-run
    python3 scripts/install.py --check                                 # 配布物の整合を検査する
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NORMS = "~/.agent-norms"
TOOLS = ("claude", "codex", "kiro")


def load_manifest() -> dict:
    return json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def compose_entry(manifest: dict) -> str:
    entry = manifest["entry"]
    parts = [entry["heading"]] + [read(src).rstrip("\n") for src in entry["sources"]]
    return "\n\n".join(parts) + "\n"


def role_body(role: dict) -> str:
    return "\n".join(read(src).rstrip("\n") + "\n" for src in role["sources"])


def render_role(name: str, role: dict, tool: str, home_skills: Path | None) -> tuple[str, str]:
    """(ファイル名, 中身) を返す。"""
    cfg = role[tool]
    body = role_body(role)
    fmt = load_manifest()["tools"][tool]["agent_format"]
    if fmt == "claude-md":
        head = (f"---\nname: {name}\ndescription: {role['description']}\n"
                f"model: {cfg['model']}\neffort: {cfg['effort']}\n---\n\n")
        return f"{name}.md", head + body
    if fmt == "codex-toml":
        # TOML の基本文字列は JSON の文字列エスケープと互換(\n \" \\ \uXXXX)
        lines = [
            f"name = {json.dumps(name, ensure_ascii=False)}",
            f"description = {json.dumps(role['description'], ensure_ascii=False)}",
            f"model = {json.dumps(cfg['model'])}",
            f"model_reasoning_effort = {json.dumps(cfg['effort'])}",
            f"developer_instructions = {json.dumps(body, ensure_ascii=False)}",
        ]
        return f"{name}.toml", "\n".join(lines) + "\n"
    if fmt == "kiro-md":
        resources = ["skill://.kiro/skills/**/SKILL.md"]
        if home_skills is not None:
            resources.append(f"skill://{home_skills}/**/SKILL.md")
        head = [
            "---",
            f"name: {name}",
            f"description: {role['description']}",
            f"model: {cfg['model']}",
            f"tools: {json.dumps(cfg['tools'])}",
            "resources:",
            *[f"  - {r}" for r in resources],
            "---",
            "",
        ]
        return f"{name}.md", "\n".join(head) + "\n" + body
    raise ValueError(f"unknown agent format: {fmt}")


class Installer:
    def __init__(self, norms_dir: str, dry_run: bool, force: bool):
        self.norms_dir = norms_dir.rstrip("/")
        self.dry_run = dry_run
        self.force = force
        self.written: list[str] = []
        self.skipped: list[str] = []
        self.notes: list[str] = []

    def text(self, s: str) -> str:
        if self.norms_dir != DEFAULT_NORMS:
            s = s.replace(DEFAULT_NORMS + "/", self.norms_dir + "/")
        return s

    def put(self, dest: Path, content: str) -> None:
        dest = dest.expanduser()
        content = self.text(content)
        if dest.exists():
            if dest.read_text(encoding="utf-8") == content:
                return
            if not self.force:
                self.skipped.append(str(dest))
                return
        self.written.append(str(dest))
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    def install_home(self, manifest: dict, tool: str, skills_to_home: bool) -> None:
        nd = Path(self.norms_dir).expanduser()
        tree = ROOT / manifest["norms"]["tree"]
        for src in sorted(tree.rglob("*")):
            if src.is_file():
                self.put(nd / src.relative_to(tree), src.read_text(encoding="utf-8"))
        for dest, src in manifest["norms"]["extra"].items():
            self.put(nd / dest, read(src))
        entry = compose_entry(manifest)
        self.put(nd / "AGENTS.md", entry)

        t = manifest["tools"][tool]
        if "entry_copy" in t:
            self.put(Path(t["entry_copy"]), entry)
        if "entry_import" in t:
            target = Path(t["entry_import"]).expanduser()
            line = f"@{self.norms_dir}/AGENTS.md"
            if not target.exists():
                self.put(target, line + "\n")
            elif line not in target.read_text(encoding="utf-8"):
                self.notes.append(f"{target} は既にあるので書き換えていない。先頭付近に次の1行を足す: {line}")

        if skills_to_home:
            self.install_skills(Path(t["skills_home"]))

    def install_skills(self, dest_root: Path) -> None:
        for skill in sorted((ROOT / "shared/skills").iterdir()):
            src = skill / "SKILL.md"
            if src.is_file():
                self.put(dest_root / skill.name / "SKILL.md", src.read_text(encoding="utf-8"))

    def install_project(self, manifest: dict, tool: str, project: Path, skills_to_project: bool) -> None:
        t = manifest["tools"][tool]
        home_skills = None if skills_to_project else Path(t["skills_home"]).expanduser()
        for name, role in manifest["roles"].items():
            if tool not in role:
                continue
            fname, content = render_role(name, role, tool, home_skills)
            self.put(project / t["agents_project"] / fname, content)
        for dest, src in manifest["project_templates"].items():
            if tool == "kiro" and dest == "docs/dev/TASKS.md":
                continue  # Kiro では spec の tasks.md を台帳にする(adapters/kiro/runtime.md「台帳」)
            self.put(project / dest, read(src))
        for dest, src in t["project_extra"].items():
            self.put(project / dest, read(src))
        if skills_to_project:
            self.install_skills(project / t["skills_project"])
        if tool == "claude" and (project / "CLAUDE.md").exists():
            text = (project / "CLAUDE.md").read_text(encoding="utf-8")
            if "@AGENTS.md" not in text:
                self.notes.append(f"{project / 'CLAUDE.md'} があると AGENTS.md は直接読まれない。先頭に @AGENTS.md の1行を足す")

    def report(self) -> None:
        verb = "書き込む予定" if self.dry_run else "書き込んだ"
        print(f"{verb}: {len(self.written)} 件")
        for p in self.written:
            print(f"  + {p}")
        if self.skipped:
            print(f"既にあり中身が違うので上書きしなかった: {len(self.skipped)} 件(上書きするなら --force)")
            for p in self.skipped:
                print(f"  = {p}")
        for n in self.notes:
            print(f"要対応: {n}")


# ---- 検査 -------------------------------------------------------------------

MODEL_ID = re.compile(r"\b(claude-(opus|sonnet|haiku|fable)-[0-9]|gpt-[0-9])")
TOOL_PATH = re.compile(r"~/\.claude/|`\.claude/|\.codex/|\.kiro/")
LINK = re.compile(r"\]\(([^)#\s]+)(#[^)]*)?\)")


def check() -> int:
    manifest = load_manifest()
    errors: list[str] = []

    def exists(rel: str, where: str) -> None:
        if not (ROOT / rel).is_file():
            errors.append(f"{where}: {rel} が無い")

    for src in manifest["entry"]["sources"]:
        exists(src, "entry")
    for dest, src in manifest["norms"]["extra"].items():
        exists(src, f"norms.extra[{dest}]")
    for dest, src in manifest["project_templates"].items():
        exists(src, f"project_templates[{dest}]")
    for name, role in manifest["roles"].items():
        for src in role["sources"]:
            exists(src, f"roles.{name}")
        tools = [t for t in TOOLS if t in role]
        if not tools:
            errors.append(f"roles.{name}: どのツールの設定も無い")
        # 実装ループが起動する role は3ツールすべてに要る
        if name in ("implementer", "implementer-advanced", "reviewer") and len(tools) != len(TOOLS):
            errors.append(f"roles.{name}: {set(TOOLS) - set(tools)} の設定が無い")
    for tool, t in manifest["tools"].items():
        for dest, src in t["project_extra"].items():
            exists(src, f"tools.{tool}.project_extra[{dest}]")

    # ツール共通の原本にモデルIDとツール固有の置き場所を書かない(adapter の仕事)
    for path in sorted((ROOT / "shared").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MODEL_ID.search(line):
                errors.append(f"{rel}:{i}: ツール共通の原本にモデルIDがある")
            if TOOL_PATH.search(line):
                errors.append(f"{rel}:{i}: ツール共通の原本にツール固有の置き場所がある")

    # スキルの frontmatter の name がディレクトリ名と一致する
    for skill in sorted((ROOT / "shared/skills").iterdir()):
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"---\nname: ([^\n]+)\n", text)
        if not m or m.group(1).strip() != skill.name:
            errors.append(f"shared/skills/{skill.name}/SKILL.md: frontmatter の name がディレクトリ名と一致しない")

    # リポジトリ内の相対リンクが解決する
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for target, _ in LINK.findall(line):
                if re.match(r"[a-z]+:", target):
                    continue
                if not (path.parent / target).exists():
                    errors.append(f"{path.relative_to(ROOT)}:{i}: リンク先 {target} が無い")

    # 入口は Codex の読み込み上限(プロジェクト指示との合計)に余裕を残す
    size = len(compose_entry(manifest).encode("utf-8"))
    if size > 16 * 1024:
        errors.append(f"入口 AGENTS.md が {size} バイト。16KiB 以下に収める")

    # 全ツール・全 role の組み立てが通る
    for name, role in manifest["roles"].items():
        for tool in TOOLS:
            if tool in role:
                render_role(name, role, tool, Path("~/.kiro/skills") if tool == "kiro" else None)

    for e in errors:
        print(e)
    print(f"check: {'NG' if errors else 'OK'}(入口 AGENTS.md {size} バイト)")
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tool", choices=TOOLS)
    ap.add_argument("--home", action="store_true", help="規範・入口・スキルをユーザー単位へ置く")
    ap.add_argument("--project", type=Path, help="role 定義と雛形を置くプロジェクトのパス")
    ap.add_argument("--skills-in-project", action="store_true", help="スキルをユーザー単位ではなくプロジェクトへ置く")
    ap.add_argument("--norms-dir", default=DEFAULT_NORMS, help=f"規範の置き場(既定 {DEFAULT_NORMS})")
    ap.add_argument("--dry-run", action="store_true", help="書き込まずに予定だけ表示する")
    ap.add_argument("--force", action="store_true", help="中身の違う既存ファイルも上書きする")
    ap.add_argument("--check", action="store_true", help="配布物の整合を検査する")
    args = ap.parse_args()

    if args.check:
        return check()
    if not args.tool or not (args.home or args.project):
        ap.error("--tool と、--home / --project の少なくとも一方が要る(検査だけなら --check)")

    manifest = load_manifest()
    inst = Installer(args.norms_dir, args.dry_run, args.force)
    if args.home:
        inst.install_home(manifest, args.tool, skills_to_home=not args.skills_in_project)
    if args.project:
        project = args.project.expanduser().resolve()
        if not project.is_dir():
            ap.error(f"{project} はディレクトリではない")
        inst.install_project(manifest, args.tool, project, skills_to_project=args.skills_in_project)
    inst.report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
