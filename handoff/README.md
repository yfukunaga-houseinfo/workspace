# イルサ ⇄ パリス 連携プロトコル

メインPCの秘書 **イルサ** と、常時起動側（このリポジトリ）の秘書 **パリス／クレア** が
非同期で仕事を受け渡すための共通ルール。AI同士は直接つながらないため、
**このGitリポジトリを共有メッセージボックス**として使う。

## 仕組み（リポジトリ＝バス）

```
イルサ（メインPC）                     パリス（クラウド/常時起動）
   │  ① 依頼を書いて push                 │
   ├───────────►  handoff/to-paris/  ────►├ ② pull して着手
   │                                       │
   │  ④ pull して受領          handoff/to-ilsa/  ◄──┤ ③ 結果を書いて push
   ◄───────────────────────────────────────┘
```

- **`handoff/to-paris/`** … イルサ → パリス への依頼（パリスのインボックス）
- **`handoff/to-ilsa/`** … パリス → イルサ への報告・成果（イルサのインボックス）

両者とも、作業の前に `git pull`、書いたら `git commit && git push` する。

## ファイル命名規則
```
YYYY-MM-DD_HHMM_<短いトピック>.md
例: 2026-06-10_0930_姫路REINS物件のマーケ調査依頼.md
```

## ファイル様式（先頭メタ＋本文）
```markdown
---
from: イルサ            # 差出人（イルサ / パリス / クレア）
to: パリス              # 宛先
date: 2026-06-10T09:30+09:00
status: NEW             # NEW / IN_PROGRESS / DONE / BLOCKED
priority: 通常          # 緊急 / 通常 / 低
deadline: 2026-06-11    # なければ「なし」
links:                  # 関連Drive/Notion/カレンダーURL等
  - <url>
---

## 依頼内容
（何を・なぜ・成功条件を一段落で）

## 補足・制約
（機密区分、出力先フォルダ、参照資料など）

## 進捗ログ（処理側が追記）
- 2026-06-10 10:05 パリス: 着手。Drive資料3件を確認。
```

## ステータスの流れ
`NEW` →（着手）→ `IN_PROGRESS` →（完了）→ `DONE`
- 着手不可・要判断は `BLOCKED` にし、理由と必要な判断を本文に書く。
- 完了時は、依頼ファイルの status を `DONE` に更新し、
  成果・結果は `handoff/to-ilsa/` 側に新規ファイルとして書く（リンクで相互参照）。

## ライブ通知（任意・推奨）
push しただけでは相手は気づけないため、合図を併用する:
- 既存のSlack秘書チャンネル（Dispatch）に
  「📥 handoff push: <ファイル名>（to-paris / to-ilsa）」と一報を入れる。
- 緊急（priority: 緊急）は必ずSlackで合図する。

---

## メインPC側（イルサ）に追記する設定スニペット
イルサのグローバル `CLAUDE.md` か `Secretary\CLAUDE.md` に、以下を追記してください。
（このリポジトリをメインPCにクローンしておくこと）

```markdown
## 連携相手: パリス（常時起動side / クラウド）
- リポジトリ: yfukunaga-houseinfo/workspace（ローカルにclone済み）
- パリスへ依頼する: handoff/to-paris/ に YYYY-MM-DD_HHMM_<topic>.md を作成し commit & push。
- パリスからの報告を受ける: 作業前に git pull し handoff/to-ilsa/ を確認。
- 受領したら相手ファイルの status を DONE に更新して push。
- 合図はSlack秘書チャンネルに「handoff push: <file>」で一報。
```
