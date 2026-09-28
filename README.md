# ai-dev-harness

コーディングエージェントに**実装タスクを1件ずつ完結させる**ための作業規範・role 定義・スキル一式。**Claude Code・Codex・Kiro** で使える。

タスク台帳を入力に、「実装 → 検証 → AIレビュー → MR/PR提出」を回し、必要な承認・本流への取り込みを確認してタスクを完了にする。**着地の仕方はプロジェクトの規約から読み取る** — 規約が無ければ MR/PR を作って止まり、マージは人が行う。

## スコープ

**このハーネスが自動化するのは、タスク台帳を入力とする実装ループだけ。**

| 対象 | |
|---|---|
| 実装ループ(実装 → 検証 → レビュー → 着地) | **対象** |
| 実装中に使う定型手順(バグ調査・契約変更・影響調査・引き継ぎなど) | **対象** |
| 仕様変更時のドキュメント同期(`spec-change`) | **対象** |
| 仕様からタスクへの分解 | **Kiro でだけ対象**(Kiro の spec の流れで分解し、その `tasks.md` を台帳にする)。Claude Code・Codex では対象外 |
| 仕様策定 | 対象外 |
| リリース判断 | 対象外(人が行う) |

Claude Code・Codex では、`TASKS.md`(タスク台帳)と決定記録を**このハーネスの外で作る**。ループはそれを読み、決定記録には追記する。台帳の**書式**だけは実装ループが読むので `shared/project/docs-dev/TASKS.md.template` に定めてある。

## 前提と非前提

**要らないもの**:

- **hooks** — 一切使わない。hooks が使えない環境でもそのまま動く
- **自動承認 / 許可のバイパス** — コマンドごとに承認が要る環境を前提にしている(Claude Code での承認回数の減らし方は [docs/adoption/permissions.md](docs/adoption/permissions.md))
- **特定のホスティング** — GitLab / GitHub / GitHub Enterprise のいずれでもよい。MR/PR を作る操作はリポジトリの規約から読み取る
- **クラウド実行環境** — ローカルのみで完結する

**要るもの**: サブエージェントを起動できるコーディングエージェント(Claude Code・Codex・Kiro)、git リポジトリ、インストーラを動かす Python 3。

## 構成

```
shared/         ツール共通の原本
  norms/          作業規範(最重要ルール・運用ルール・設計原則・引き継ぎ・指示の書き方)
  entry.md        常時読み込みの入口のうち、作業ごとに読む節の案内(最重要ルールと合わせて AGENTS.md になる)
  skills/         next-task(実装ループ)+ 定型手順
  roles/          implementer / implementer-advanced / reviewer の手順(モデル指定なし)
  project/        プロジェクトの AGENTS.md と docs/dev/(TASKS / WORKFLOW / IMPLEMENTATION-RULES)の雛形
adapters/       ツールごとの差分
  claude/         runtime.md(モデル・置き場所・起動方法)、settings.json.template
  codex/          runtime.md
  kiro/           runtime.md(tasks.md を台帳にする読み替えを含む)、steering、orchestrator 定義
manifest.json   原本から各ツールの置き場所・書式への対応
scripts/install.py  インストーラ兼検査
docs/adoption/  permissions.md(Claude Code)/ merge-request-flow.md
```

**ツール共通の原本(`shared/`)にはモデル名もツール固有の置き場所も書かない。** それらは `adapters/<ツール>/runtime.md` と `manifest.json` が持ち、`install.py --check` が混入を検査する。

## 導入

1. **規範・入口・スキルをユーザー単位に置く**:

   ```bash
   python3 scripts/install.py --tool <claude|codex|kiro> --home --dry-run   # 何が置かれるかを見る
   python3 scripts/install.py --tool <claude|codex|kiro> --home
   ```

   規範は `~/.agent-norms/` に入り、常時読み込みの入口 `AGENTS.md`(最重要ルール + 作業ごとに読む節の案内)が組み立てられる。
   **入口の配線を飛ばすと、規範は一度も読まれない。** ファイルを置くだけでは自動読み込みされず、しかもエラーは出ないので、動いているつもりで完了条件もセルフチェックの義務も全部抜ける。インストーラが配線できなかったときは「要対応」として表示する
2. **role 定義と雛形をプロジェクトに置く**:

   ```bash
   python3 scripts/install.py --tool <claude|codex|kiro> --project <プロジェクトのパス>
   ```

   プロジェクト直下の `AGENTS.md` と `docs/dev/` の雛形を埋める。**既存のファイルは上書きしない**(上書きするなら `--force`)
3. **モデルの割り当てを確かめる**: 下の「役割とモデルの割り当て」
4. **承認設定を試す**(Claude Code): [docs/adoption/permissions.md](docs/adoption/permissions.md)
5. **台帳を準備する**: Claude Code・Codex は `docs/dev/TASKS.md`。既存の台帳は `TASKS.md.template` の移行手順で確認し、旧 `[x]` を未確認のまま依存完了とみなさない。Kiro は spec の `tasks.md`([adapters/kiro/runtime.md](adapters/kiro/runtime.md)「台帳」と「導入時の確認」)
6. **回す**: スキル `next-task` を呼ぶ(1回1タスク)。連続実行の方法はツールごとに違う(各 `runtime.md`)。レビュー待ちは取り直さず、中断したタスクは既存ブランチから再開する

インストーラを使わずに手で置く場合も、置き場所は各 `runtime.md` の「ファイルの置き場」、組み立て方は `manifest.json` のとおり。

## ツールごとの違い

| | Claude Code | Codex | Kiro |
|---|---|---|---|
| 入口(ユーザー単位) | `~/.claude/CLAUDE.md` から `@~/.agent-norms/AGENTS.md` を取り込む | `~/.codex/AGENTS.md`(写し) | `~/.kiro/steering/AGENTS.md`(写し) |
| プロジェクトの指示 | `AGENTS.md`(`CLAUDE.md` があるならそこに `@AGENTS.md`) | `AGENTS.md` | `AGENTS.md` |
| role 定義 | `.claude/agents/*.md` | `.codex/agents/*.toml` | `.kiro/agents/*.md` |
| 台帳 | `docs/dev/TASKS.md` | `docs/dev/TASKS.md` | spec の `tasks.md` |
| 詳細 | [claude](adapters/claude/runtime.md) | [codex](adapters/codex/runtime.md) | [kiro](adapters/kiro/runtime.md) |

**写しの入口は、規範を更新したらインストーラで入れ直す。** Codex と Kiro の `AGENTS.md` は取り込み(`@path`)を展開しないので、単体で読める写しを置いている。

## ドキュメントの読み方

- 状態・依存・記録の書式: [タスク台帳テンプレート](shared/project/docs-dev/TASKS.md.template)
- 実行・指摘単位の再レビュー・中断と再開: [next-task](shared/skills/next-task/SKILL.md)
- プロジェクト固有の着地とレビュー証跡: [ワークフローテンプレート](shared/project/docs-dev/WORKFLOW.md.template)
- 導入時のMR/PR運用: [MR/PRフロー](docs/adoption/merge-request-flow.md)

`shared/norms/` は判断・品質の共通規範、`shared/skills/` は実行手順、`shared/project/` は導入先で埋める状態・規約。コピーしたテンプレートの参照先や節名を変更したら、利用するスキルにも対応を伝える。

## 役割とモデルの割り当て

| role | 何をするか | 使う場面 |
|---|---|---|
| orchestrator | タスク選定・委譲・**検証の実行**・着地処理 | メインセッション(Kiro では `orchestrator` エージェント) |
| implementer(standard) | 実装 | 実装の既定の委譲先 |
| implementer-advanced(advanced) | 実装 | 台帳の `#### impl` が `advanced` のタスクと、重大指摘による差し戻し後 |
| reviewer | 仕様適合と論理矛盾のレビュー | 全タスク。実装の文脈を持たずに起動する |

**台帳が指定するのは実装 tier(`standard` / `advanced`)で、モデル名ではない。** どの role をどのモデルで動かすかは `manifest.json` の `roles` に書いてあり、インストーラが各ツールの role 定義へ書き込む。**同梱の値は執筆時点のもの**なので、導入時に確かめて直す。

orchestrator のモデルはセッションを起動する側で選ぶ(推奨は各 `runtime.md` の「役割とモデル」。Kiro は `orchestrator` エージェントの定義で固定する)。

**3役すべてに同じモデルを割り当ててよい。** 枠が限られるなら全て下位モデルで始め、品質のために必要になった箇所だけ上げる。上げる順の推奨は **reviewer → implementer-advanced → orchestrator**。

**モデルは完全な識別子で書く。** エイリアス(`opus` / `sonnet` 等)は更新で解決先が無言に変わる。Kiro は識別子の一覧が公式ドキュメントに無いので `/model` で確かめる。

## 旧版からの移行

`norms/` と `kit/` だった版から移る場合:

- 規範の置き場が `~/.claude/norms/` から `~/.agent-norms/` に変わった。`~/.claude/CLAUDE.md` の `@norms/CLAUDE.md` を `@~/.agent-norms/AGENTS.md` に置き換え、古い `~/.claude/norms/` は消してよい
- **常時読み込みが減った。** 以前は運用ルール全文(`working-norms.md`)を毎回読んでいたが、今は最重要ルールと「作業ごとに読む節」の案内だけを読み、詳細はスキルと role が手順の中で読む
- プロジェクトの `CLAUDE.md`(`kit/settings/CLAUDE.md.template` から作ったもの)は、`AGENTS.md` へ改名するか、`CLAUDE.md` の先頭に `@AGENTS.md` を置いて中身を移す
- 台帳の `#### impl` はモデルIDから実装 tier(`standard` / `advanced`)に変わった。書き換え方は `TASKS.md.template`「既存台帳からの移行」
- 本流ブランチの宣言は `.claude/mainline-branch` から `docs/dev/mainline-branch` に移った
- role 定義は `implementer-advanced` が増えた。インストーラの `--project` で入れ直す

## 同梱スキル

**実装ループ**: `next-task`

**実装ループの中核**: `bug-hunt` / `test-first-fix` / `impact-scan` / `contract-change` / `self-review` / `release-check` / `spec-check`

**横断**: `handoff` / `feedback-capture` / `session-economy` / `doc-audit` / `decision-log` / `spec-change` / `issue-intake`

各スキルが何をするか・いつ使うかは `shared/skills/<名前>/SKILL.md` の `description` にある。

## ライセンス

**MIT-0(MIT No Attribution)**。詳細は [LICENSE](LICENSE)。

MIT から「著作権表示とライセンス条文を複製物に含めること」の一文を外したもので、**出典を明記せずに取り込める**。自分のスキルや規範と混ぜて取り込む使い方を想定しているため — どこまでがこのハーネス由来かを追跡し続けるのは現実的でない。OSI 承認済み、SPDX 識別子は `MIT-0`。
