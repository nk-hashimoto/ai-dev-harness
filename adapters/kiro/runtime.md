# Kiro runtime adapter

共通の規範・スキル・role が「runtime adapter が持つ」と書いている事柄の、Kiro での答え。

**確認の状態**: Kiro の公式ドキュメント(kiro.dev/docs。specs・steering・skills・custom agents・sub-agents・models の各ページ)を読んで書いた。
**`tasks.md` の正確な書式は公式ドキュメントに記載が無く**(Kiro が生成する前提のため)、下の「台帳」の対応表は**未検証**。導入時に「導入時の確認」を行う。

## 役割とモデル

| role | 定義 |
|---|---|
| orchestrator | `.kiro/agents/orchestrator.md`(セッションをこのエージェントで始める) |
| implementer(standard) | `.kiro/agents/implementer.md` |
| implementer-advanced(advanced) | `.kiro/agents/implementer-advanced.md` |
| reviewer | `.kiro/agents/reviewer.md` |

- **role 定義のモデルは、配布元の `manifest.json` の `roles` が正**(インストーラが定義へ書き込む)。**値は執筆時点のもの。** Kiro で選べるモデルは Claude Code と同じとは限らない(執筆時点では Opus 5.5 が無く、Opus 5 が最新)
- **定義の `model:` に書く識別子は `/model` で確かめる。** 公式ドキュメントに一覧が無く、同梱の識別子は未検証
- **指定したモデルが使えないと、既定のモデルで動き続け、警告だけが出る。** 規範の「未知の値を近い既定へ黙って落とさない」に反するので、導入時と定義を変えたときに警告が出ていないかを見る
- **orchestrator のモデルを固定するには、セッションを `orchestrator` エージェントで始める。** 既定のエージェントで始めると、モデルはチャットで選んだものになる
- **effort(推論量)は role ごとに固定できない。** 定義に effort の欄が無く、セッション単位で選ぶ(IDE はモデル選択の Effort、CLI は `/model` か `--effort`)。サブエージェントが親の effort を引き継ぐかは公式ドキュメントに記載が無い
- 消費クレジットの倍率はモデルで違う(執筆時点: Opus 5 は Sonnet 5 の約1.7倍)。枠が限られるなら reviewer 以外を Sonnet 5 に下げる

## ファイルの置き場

| もの | ユーザー単位 | プロジェクト単位 |
|---|---|---|
| 入口(常時読み込み) | `~/.kiro/steering/AGENTS.md`(`~/.agent-norms/AGENTS.md` の写し) | `AGENTS.md`(ワークスペース直下) |
| スキル | `~/.kiro/skills/<名前>/SKILL.md`(IDE・CLI のみ) | `.kiro/skills/<名前>/SKILL.md` |
| role 定義 | `~/.kiro/agents/<role>.md` | `.kiro/agents/<role>.md` |
| タスク洗い出しの規約 | — | `.kiro/steering/harness-tasks.md` |
| spec | — | `.kiro/specs/<spec名>/{requirements.md, design.md, tasks.md}` |

- **`AGENTS.md` は常に読み込まれ、steering の読み込み条件(`inclusion`)は付けられない。** 入口は写しなので、`~/.agent-norms/` を更新したらインストーラで入れ直す
- **`~/.agent-norms/` はワークスペースの外にある。** 読むときに許可を求められることがある。Kiro Web などホームディレクトリの無い実行環境では、インストーラの `--norms-dir` で規範をワークスペース内(例: `.agent-norms/`)へ置く
- **Kiro CLI は steering の読み込み条件に対応しておらず、`.kiro/steering/` の全ファイルを読む**(公式ドキュメントの記載)。`harness-tasks.md` は小さく保つ

## role 定義の書式

```markdown
---
name: <role>
description: <いつ使うか。メインエージェントがサブエージェントを選ぶ材料になる>
model: <モデル識別子>
tools: ["read", "write", "shell"]        orchestrator には "subagent" も要る
resources:
  - skill://.kiro/skills/**/SKILL.md
---
本文 = role の手順(shared/roles/ から生成される)
```

- **自作エージェントがスキルを自動で読むかは、公式ドキュメント内で記述が食い違っている。** 生成する定義では `resources` にスキルを明示している
- サブエージェントとして起動されたエージェントは、定義の `tools` にある道具しか使えない

## role の起動と再開

- **起動**: orchestrator が、role 名を名指ししてサブエージェントとして起動する(例: 「`reviewer` サブエージェントで T の差分をレビューする」)。サブエージェントは会話履歴を引き継がず、自分のコンテキストで動くので、reviewer の独立性の条件を満たす
- **承認を求められない起動では、承認の要る道具を使うと即座に失敗する。** 実装とレビューを任せる role は信頼済みにしておく(`trustedAgents`)か、`permissions` で必要な操作を許可する
- **再開**: 終わったサブエージェントを続ける手段は、読んだ範囲の公式ドキュメント(sub-agents・custom agents)には見当たらなかった。**差し戻し・再レビューは毎回新規に起動し、前ラウンドまでの指摘一覧(番号・内容・判定・未解消回数)を添える**(スキル `next-task` の再開できないときの手順)
- Kiro は「Run all Tasks」で独立したタスクを並列に実行するが、**このハーネスでは使わない**(下の「台帳」)
- **スキル `parallel-tasks` は使わない。** 必要なバックグラウンド起動と同じ体への続行の手段が、読んだ範囲の公式ドキュメントに見当たらず、worktree での運用も未確認

## 連続実行とタスク管理

- 連続実行: orchestrator エージェントのセッションで、スキル `next-task` を1回に1タスクずつ呼ぶ。1セッションで回し続けるとコンテキストが伸びるので、区切りでセッションを分ける
- タスク管理ツール: Kiro の todo リスト(道具のタグ `todo_list`)か、作業メモのファイル

## 台帳

**Kiro では、spec の `tasks.md` を台帳にする。** `docs/dev/TASKS.md` は使わない。タスクの洗い出しは Kiro の spec の流れ(要件 → 設計 → タスク)で行い、その書き方は `.kiro/steering/harness-tasks.md` が定める。

### 対象の spec

`WORKFLOW.md` §3「台帳の保存先」に、いま回している spec の名前を書く。書いていなければ、未完了のタスクが残る spec が1つならそれ、複数なら人に聞く。

### `TASKS.md.template` の節との対応(未検証)

スキル `next-task` と `~/.agent-norms/templates/TASKS.md.template` が「台帳の節」と呼ぶものを、`tasks.md` では次のように読み替える。

| TASKS.md の節 | tasks.md での表し方 |
|---|---|
| タスク(1つの `###` 見出し) | **トップレベルの番号付きタスク**(`- [ ] 2. …`)。その下のサブタスク(`2.1` `2.2` …)はそのタスクの実装手順として扱い、1件ずつ選ばない |
| タスクID | `<spec名>/<番号>`(例: `user-auth/2`)。報告・申し送り・出所ラベルはこの形で書く |
| `#### 状態` | タスクの下の箇条書き `- 状態: 未着手` 等。**チェックボックスは状態の正にしない**(下の注意) |
| `#### 種別` / `#### impl` / `#### deps` | 同じく箇条書き `- 種別: 機能` / `- impl: advanced` / `- deps: user-auth/1` |
| `#### spec` | Kiro が付ける要件参照(`_Requirements: 1.1, 2.3_` の形)と、`design.md` の該当節 |
| `#### 内容` | Kiro が生成したタスク本文とサブタスク |
| `#### DoD` | 箇条書き `- DoD: …`(1行1条件) |
| `#### ⚠要人間確認` | 箇条書き `- ⚠要人間確認: …` |
| `#### 実行記録` | `tasks.md` には書かず、`.kiro/specs/<spec名>/runs.md` にタスクID単位で書く(Kiro の再生成で消えないように) |
| `tasks-done/` への退避 | **しない**。完了したタスクも `tasks.md` に残す(Kiro の spec の一部なので) |

### 注意

- **Kiro 自身のタスク実行(タスクの「Start task」・「Run all Tasks」)を使わない。** Kiro の実行は、検証・独立レビュー・MR/PR の手前でタスクを完了扱いにする。このハーネスの完了は、スキル `next-task` が承認と本流への取り込みを確かめてからで、それより前にチェックが付くと依存タスクが早く解禁される
- **チェックボックスは状態の正にしない。** 上の理由で Kiro が付けたチェックが残りうるので、`- 状態:` の行を正にする。`[x]` なのに状態が完了でないタスクは、同テンプレートの「チェック状態と状態欄が矛盾したら」に従って実際の変更・MR/PR を確かめてから直す
- **Kiro が任意(optional)と印を付けたタスクは選ばない。** 人が印を外したら通常のタスクとして扱う
- **要件や設計を直して `tasks.md` を同期し直したら**(「Sync Files」等)、ハーネスの箇条書き(`- 状態:` 等)が残っているかを差分で確かめる。消えていたら `runs.md` と git の履歴から戻す

### 導入時の確認

1. Kiro で小さな spec を1つ作り、生成された `tasks.md` の実際の書式(チェックボックス・番号・サブタスク・要件参照・任意の印)を見る
2. 上の対応表の読み替えがその書式に当てはまるかを確かめ、合わない箇所はこのファイルを直す
3. ハーネスの箇条書きを足した `tasks.md` を Kiro のタスク画面で開き、Kiro が書式を読めること(タスクが一覧に出ること)を確かめる
