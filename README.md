# ai-dev-harness

コーディングエージェントに**実装タスクを1件ずつ完結させる**ための作業規範・サブエージェント定義・スキル一式。

タスク台帳を入力に、「実装 → 検証 → レビュー → コミット → 着地」を1周として回す。**着地の仕方はプロジェクトの規約から読み取る** — 規約が無ければ MR/PR を作って止まり、マージは人が行う。

## スコープ

**このハーネスが自動化するのは、タスク台帳を入力とする実装ループだけ。**

| 対象 | |
|---|---|
| 実装ループ(実装 → 検証 → レビュー → 着地) | **対象** |
| 実装中に使う定型手順(バグ調査・契約変更・影響調査・引き継ぎなど) | **対象** |
| 仕様変更時のドキュメント同期(`spec-change`) | **対象** |
| 仕様策定 | 対象外 |
| 仕様からタスクへの分解 | 対象外 |
| リリース判断 | 対象外(人が行う) |

`TASKS.md`(タスク台帳)と決定記録は、**このハーネスの外で作る**。作り方(仕様をどうタスクへ割るか)は範囲外で、ループはそれを読み、決定記録には追記する。台帳の**書式**だけは `/next-task` が読むので `kit/docs-dev/TASKS.md.template` に定めてある。

## 前提と非前提

**要らないもの**:

- **hooks** — 一切使わない。hooks が使えない環境でもそのまま動く
- **自動承認 / 許可のバイパス** — コマンドごとに承認が要る環境を前提にしている(承認回数の減らし方は [docs/adoption/permissions.md](docs/adoption/permissions.md))
- **特定のホスティング** — GitLab / GitHub / GitHub Enterprise のいずれでもよい。MR/PR を作る操作はリポジトリの規約から読み取る
- **クラウド実行環境** — ローカルのみで完結する

**要るもの**: サブエージェントを起動できるコーディングエージェント(Claude Code など)と、git リポジトリ。

## 構成

```
norms/          作業規範。プロジェクト非依存
  CLAUDE.md                     常時読み込みの入口(下2つを import する)
  00-priority-rules.md          最重要ルール10件(優先順位つき)【常時】
  01-engineering-principles.md  設計思想・品質基準・レビュー基準
  02-thought-processes.md       判断の内側(立ち止まるトリガー・比較軸)
  03-implementation-pitfalls.md 実装で失敗しやすい14パターン
  04-handoff-protocol.md        セッション間の引き継ぎ
  05-orchestration-notes.md     上位モデルへの指示の書き方(呼び出し側向け)
  skill-design.md               Skill の命名・起動条件の決め方
  working-norms.md              運用ルールの凝縮版 + 完了条件(DoD)【常時】
  templates/handoff.md          引き継ぎ文書のテンプレート

kit/            プロジェクトへコピーする一式
  agents/       implementer / reviewer
  skills/       next-task(実装ループ)+ 定型手順13件
  settings/     CLAUDE.md.template / settings.json.template
  docs-dev/     TASKS / WORKFLOW / IMPLEMENTATION-RULES のテンプレート

docs/adoption/  permissions.md / merge-request-flow.md
```

## 導入

1. **規範を置き、常時読み込みに配線する**: `norms/` を `~/.claude/norms/` へコピーし、**`~/.claude/CLAUDE.md` に次の1行を書く**(無ければ作る)。

   ```
   @norms/CLAUDE.md
   ```

   **この配線を飛ばすと、規範は一度も読まれない。** ファイルを置くだけでは自動読み込みされず、しかもエラーは出ないので、動いているつもりで完了条件もセルフチェックの義務も全部抜ける。`norms/CLAUDE.md` が `00-priority-rules.md` と `working-norms.md` を import し、残りは必要時に読む扱いになる(スキルは `~/.claude/norms/` のパスを参照している)
2. **スキルを置く**: `kit/skills/*` を `~/.claude/skills/` へコピーする(全プロジェクトで使う場合)
3. **エージェント定義を置く**: `kit/agents/*` を `~/.claude/agents/` またはプロジェクトの `.claude/agents/` へコピーする
4. **プロジェクト側を用意する**: `kit/settings/CLAUDE.md.template` と `kit/docs-dev/*.template` を、プロジェクトの `CLAUDE.md` / `docs/dev/` として埋める
5. **承認設定を試す**: `kit/settings/settings.json.template` をプロジェクトの `.claude/settings.json` に当て、効くかを確かめる([手順](docs/adoption/permissions.md))
6. **回す**: `/next-task`(1タスク)または `/loop /next-task`(連続)

**新しく置いたエージェント定義は、セッションを再起動するまで認識されない**(`Agent type not found` になる)。

## 3役とモデルの割り当て

| 役 | 何をするか | 実体 |
|---|---|---|
| オーケストレーター | タスク選定・委譲・**検証の実行**・着地処理 | メインセッション |
| implementer | 実装 | `kit/agents/implementer.md` |
| reviewer | 仕様適合と論理矛盾のレビュー | `kit/agents/reviewer.md` |

**タスクによって実装モデルを変えたくなったら、`implementer.md` を複製して `model:` だけ変える**(例: `implementer-<モデル名>.md`)。Agent ツールの `model` パラメータはフルモデルIDを受け付けないため、**モデルの数だけ定義を用意して `subagent_type` で選ぶ**しかない。台帳の `#### impl` はその定義の選択に使う。

**3役すべてに同じモデルを割り当ててよい。** 枠が限られるなら全て下位モデルで始め、品質のために必要になった箇所だけ上げる。上げる順の推奨は **reviewer → `#### impl` 指定タスクの implementer → オーケストレーター**。

**モデルはフルモデルID(`claude-sonnet-5` など)で書く。** エイリアス(`opus` / `sonnet`)は CLI の更新で解決先が無言に変わる。

**実際のモデルIDが書いてあるのはエージェント定義の `model:` frontmatter だけで、そこが正。** プロジェクトの `CLAUDE.md` に置く役割表(`kit/settings/CLAUDE.md.template` §4)は、規範が言う「上位モデル」「下位モデル」がどの定義を指すかの対応表で、モデルIDを二重に持たない。**同梱の定義に書いてある `model:` の値は執筆時点のものなので、導入時に必ず確認する。**

## 同梱スキル

**実装ループ**: `next-task`

**実装ループの中核**: `bug-hunt` / `test-first-fix` / `impact-scan` / `contract-change` / `self-review` / `release-check` / `spec-check`

**横断**: `handoff` / `feedback-capture` / `session-economy` / `doc-audit` / `decision-log` / `spec-change`

`self-review` は**完了報告の前に必ず実行する**(呼ばれるのを待たない)。作った成果物の種類 — コード / 常設ドキュメント / 掃引・検査 / 報告 — ごとに**読み返すルールの下限が表で決まる**ので、開放的な再検証にはならない(判断で足すのは自由、減らすのは禁止)。**モデルの階層で省かない**: 一度読んだ状態と、この成果物に当てた状態は内側からは区別できず、規則を読んでいたのに自分の出力へ当てていないという失敗は階層を問わず起きる。

`release-check` は**明示的に呼んだときだけ動く**。DoD の全項目をコマンド実行で機械的に検証するもので、**その大半はループの中で別々に済んでいる**(静的検査とテストは検証の手順、diff と最悪ケースは `self-review`)。ループの外で「本当に完了と言えるか」を一度に確かめたいときに使う。

## ライセンス

**MIT-0(MIT No Attribution)**。詳細は [LICENSE](LICENSE)。

MIT から「著作権表示とライセンス条文を複製物に含めること」の一文を外したもので、**出典を明記せずに取り込める**。自分のスキルや規範と混ぜて取り込む使い方を想定しているため — どこまでがこのハーネス由来かを追跡し続けるのは現実的でない。OSI 承認済み、SPDX 識別子は `MIT-0`。
