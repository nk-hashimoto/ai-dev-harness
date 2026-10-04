# Codex runtime adapter

共通の規範・スキル・role が「runtime adapter が持つ」と書いている事柄の、Codex での答え。

**確認の状態**: この adapter の内容は、実運用している Codex 向け設定を一般化したもの。執筆時点で Codex の公式ドキュメントとの突き合わせはできていない。導入時に、下の「要確認」を公式ドキュメントで確かめる。

## 役割とモデル

| role | 定義 |
|---|---|
| orchestrator | メインセッション。推奨は `gpt-5.6-sol`・reasoning effort high(起動する側で選ぶ) |
| implementer(standard) | `.codex/agents/implementer.toml` |
| implementer-advanced(advanced) | `.codex/agents/implementer-advanced.toml` |
| reviewer | `.codex/agents/reviewer.toml` |

- **role 定義のモデルと effort は、配布元の `manifest.json` の `roles` が正**(インストーラが定義へ書き込む)。**値は執筆時点のもの**なので導入時に見直す。
  - 同梱の値で implementer と implementer-advanced が同じモデルなのは、この割り当てでは tier の違いを担当範囲(と差し戻し後の昇格)だけで表しているため。上位モデルで advanced を回したいなら、`manifest.json` の `implementer-advanced` だけを変えて入れ直す
- **モデルは role 定義に完全な識別子で書く。** 実行時に別のモデルで上書きしない

## ファイルの置き場

| もの | ユーザー単位 | プロジェクト単位 |
|---|---|---|
| 入口(常時読み込み) | `~/.codex/AGENTS.md`(`~/.agent-norms/AGENTS.md` の写し) | `AGENTS.md` |
| スキル | `~/.agents/skills/<名前>/SKILL.md` | `.agents/skills/<名前>/SKILL.md` |
| role 定義 | — | `.codex/agents/<role>.toml` |

- **`AGENTS.md` の `@path` 取り込みは展開されない**(Claude Code とは違う)。入口の `AGENTS.md` は単体で読める文章として生成してある。写しなので、`~/.agent-norms/` を更新したらインストーラで入れ直す
- **`AGENTS.md` には読み込み量の上限がある**(既定の `project_doc_max_bytes` はユーザー単位とプロジェクト単位の合計枠で 32KiB)。プロジェクトの `AGENTS.md` は現在の状態と参照先だけにし、詳細は条件付きで読む文書へ置く
- 要確認: `project_doc_max_bytes` の既定値と合計の扱い

## role 定義の書式

```toml
name = "<role>"
description = "<いつ使うか>"
model = "<完全なモデルID>"
model_reasoning_effort = "low|medium|high|xhigh|max"
developer_instructions = "<role の手順(shared/roles/ から生成される)>"
```

## role の起動と再開

- **起動**: project agent を名指しで起動する(運用側で使っている道具名は起動 = `spawn_agent`、完了待ち = `wait_agent`)。スキル `next-task` の委譲は完了を待つ
- **reviewer は新しいコンテキストで起動する**(親の会話を渡さない。`fork_turns: "none"` 相当)
- **再開**: 停止した同じエージェントへ続きを依頼する(運用側の道具名は `followup_task`)。新規起動より先に再開を試す
- 要確認: 上の道具名と引数は公式ドキュメントで確かめる
- **読み取り専用の調査**: 境界の明確な調査に限り、読み取り専用の調査 role(例: `explorer`、モデルは implementer と同じ下位モデル)を定義して使ってよい

## 連続実行とタスク管理

- 連続実行: 1回の実行で1タスクを進め、次のタスクは新しい実行で始める(スキルの手順0から)。1セッションで回し続けるとコンテキストが伸び、序盤の制約・決定が要約で薄れる
- タスク管理ツール: Codex の計画(plan)機能か、作業メモのファイル

## 並列運転(`parallel-tasks`)

スキル `parallel-tasks` が「runtime adapter が定める」と書いている事柄。

- orchestrator は `next-task` と同じ
- **起動**: `spawn_agent`、**完了待ち**: `wait_agent`、**続行**: `followup_task`。道具名は「role の起動と再開」と同じく要確認
- **作業場所の指定**: プロンプトに worktree の絶対パスを書く。サブエージェントがリポジトリの外の worktree へ書き込めるかは未確認で、並列運転の前に1本で確かめる
- **使用量の計測**: この adapter は定めていない。スキルの停止条件に従う
- **クラウド**: 隔離された checkout が1つの環境で worktree を作る運用は未確認。確認するまで使わない

## hook

このハーネスは hook を前提にしない。使う場合は Codex が公式に扱うイベントと schema だけを使う。

## 台帳

`docs/dev/TASKS.md`(書式は `TASKS.md.template`)。読み替えは不要。
