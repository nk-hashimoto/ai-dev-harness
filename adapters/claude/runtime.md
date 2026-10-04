# Claude Code runtime adapter

共通の規範・スキル・role が「runtime adapter が持つ」と書いている事柄の、Claude Code での答え。

## 役割とモデル

| role | 定義 |
|---|---|
| orchestrator | メインセッション。推奨は `claude-opus-5-5`・effort medium(起動する側で選ぶ。リポジトリからは指定できない) |
| implementer(standard) | `.claude/agents/implementer.md` |
| implementer-advanced(advanced) | `.claude/agents/implementer-advanced.md` |
| reviewer | `.claude/agents/reviewer.md` |

- **role 定義のモデルと effort は、配布元の `manifest.json` の `roles` が正**(インストーラが定義へ書き込む)。**値は執筆時点のもの。** 導入時に、使える最新のモデルと自分の使用枠に合わせて見直す。枠が限られるなら全 role を下位モデルで始め、必要になった箇所だけ上げる(上げる順の推奨は reviewer → implementer-advanced → orchestrator)
- **世代の固定は role 定義の `model:` に完全なモデルIDで書く。** `opus` / `sonnet` のようなエイリアスは、CLI の更新で解決先が無言に付け替わる(実測: 3日・パッチ1つで1世代進んだ)。確認は `claude -p --model opus --output-format json` の `canonicalModel`
- **Opus 5.5 の effort は目盛りが Opus 5 とずれている。** medium で Opus 5 の high に並ぶか上回る。Opus 5 の値をそのまま持ち込まない(ターンが長く・高くなる)。xhigh / max は品質の向上を測った作業だけに使う
- **Opus 5.5 は thinking を切れない。** 「考えるな」系の指示は消し、考える量は effort で絞る。推論を回答本文に書き出させる指示は拒否されうる
- 出典:
  - [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)
  - [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

## ファイルの置き場

| もの | ユーザー単位 | プロジェクト単位 |
|---|---|---|
| 入口(常時読み込み) | `~/.claude/CLAUDE.md` に `@~/.agent-norms/AGENTS.md` の1行 | `AGENTS.md`(下記の注意) |
| スキル | `~/.claude/skills/<名前>/SKILL.md` | `.claude/skills/<名前>/SKILL.md` |
| role 定義 | `~/.claude/agents/<role>.md` | `.claude/agents/<role>.md` |
| 権限設定 | `~/.claude/settings.json` | `.claude/settings.json`(雛形は `settings.json.template`、手順は `docs/adoption/permissions.md`) |

- **プロジェクトの `AGENTS.md` を直接読むのは Claude Code v2.1.277 以降で、同じ階層か上の階層に `CLAUDE.md` / `CLAUDE.local.md` が無いときだけ。** どちらかがあるなら、その `CLAUDE.md` の先頭に `@AGENTS.md` の1行を置く。取り込んだ `AGENTS.md` は二重には読まれない
- ユーザー単位の入口は `~/.claude/CLAUDE.md` から取り込む。公式ドキュメントが `AGENTS.md` の読み込み先として挙げているのは、作業ディレクトリとその上の階層だけ
- `~/.agent-norms/` の外部取り込みは初回に承認を求められる

## role 定義の書式

```markdown
---
name: <role>                 呼び出し時の subagent_type になる
description: <いつ使うか>     呼ぶ側が選ぶための文。対象が増えると陳腐化する固有名詞を書かない
model: <完全なモデルID>       エイリアスを書かない
effort: low|medium|high|xhigh|max
---
本文 = role の手順(shared/roles/ から生成される)
```

- **`effort:` は Agent ツール経由の起動では効くが、`claude -p --agent <name>` の経路では効かない**(実測)。環境変数 `CLAUDE_CODE_EFFORT_LEVEL` はどちらでも効く
- **新しく置いた role 定義は、セッションを再起動するまで認識されないことがある**(`Agent type '...' not found`)。時間を置いて再試行するか、セッションを開き直す

## role の起動と再開

- **起動**: Agent ツールで `subagent_type` に role 名を指定する。**`model` パラメータは渡さない** — エイリアスしか受け付けず、定義の `model:` を上書きしてしまう。スキル `next-task` の委譲は完了を待つ(`run_in_background: false`)
- **reviewer は fork(親の会話を引き継ぐ起動)にしない。** 実装の文脈を持たないことが独立レビューの前提
- **再開**: 同じエージェントへ `SendMessage` で続きを依頼する。前回の応答からプロンプトキャッシュの寿命を過ぎていると、再開は全履歴を新規トークンとして再投入するので、新規起動と同じか高くつく。寿命を過ぎていたら同じ role を新規起動する
  - 寿命は利用形態によって違う。確かめていなければ短い方を想定する
- **読み取り専用の調査**: 組み込みの Explore エージェント等を使ってよい(実装は任せない)

## 連続実行とタスク管理

- 連続実行: `/loop /next-task`。1回ごとに次の選定をスキルの手順0からやり直す
- タスク管理ツール: 組み込みの ToDo(タスク)ツール

## 並列運転(`parallel-tasks`)

スキル `parallel-tasks` が「runtime adapter が定める」と書いている事柄。

- orchestrator は `next-task` と同じ
- **起動**: Agent ツールの `run_in_background: true`。完了はバックグラウンドの結果通知で受け取る。**続行**: `SendMessage`(キャッシュの寿命の条件は「role の起動と再開」と同じ)
- **作業場所の指定**: Agent ツールに作業ディレクトリの引数は無い。プロンプトに worktree の絶対パスを書く
- **権限**: `settings.json.template` は worktree の作成・移動・削除を許可していない(`git worktree list` のみ)。並列運転する導入先で `git worktree add` / `move` / `remove` を許可する
  - サブエージェントがリポジトリの外の worktree へ書き込めるかは未確認。並列運転の前に、1本で確かめる
- **使用量の計測**: この adapter は定めていない。スキルの停止条件に従う
- **クラウド**: 隔離された checkout が1つの環境で worktree を作る運用は未確認。確認するまで使わない

## 台帳

`docs/dev/TASKS.md`(書式は `TASKS.md.template`)。読み替えは不要。
