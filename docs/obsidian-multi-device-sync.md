# Obsidian マルチデバイス同期 ＋ obsidian-skills 導入手順

メインノートPC（イルサ）と常時機能PC（パリス）の **両方から同じ Obsidian Vault を見る**ための
セットアップ手順書。方式は **Git同期（GitHubプライベートリポジトリ）**、加えて Obsidian 公式の
**obsidian-skills** を Vault に同梱して、両PCの Claude Code がノートを自然に読み書きできるようにする。

- 想定環境: **両PCともWindows** / Git先: **GitHubプライベートリポジトリ** / Vaultは**新規作成**
- 設計のキモ: **obsidian-skills を Vault内の `.claude/skills` に置く**ことで、Vaultを同期すれば
  ノートもスキルも一緒に運ばれる。→「1回入れて commit、両PCで pull すれば両方に入る」。

---

## 全体像

```
あなたのObsidian Vault（= 1つのGitリポジトリ: obsidian-vault）
├── .claude/skills/        ← obsidian-skills（5スキル）をここに同梱
├── .obsidian/             ← Obsidian設定（一部はgit除外）
├── .gitignore
└── ノート.md / .canvas / .base ...
        │  git push / pull（Obsidian Gitプラグインで自動化）
   ┌────┴─────────────┐
メインノートPC            常時機能PC
（イルサ / Claude Code）   （パリス / Claude Code）
```

> 注: これは秘書ハブ（`yfukunaga-houseinfo/workspace`）とは**別のリポジトリ**。
> Vault側に独自の `.claude` を持つので、workspace側の `.claude` とは衝突しない。

---

## 含まれる obsidian-skills（公式 kepano/obsidian-skills）

| スキル | 役割 |
|---|---|
| `obsidian-markdown` | Obsidian方言のMarkdown（内部リンク`[[ ]]`、callout等）を正しく編集 |
| `obsidian-bases` | `.base`（Obsidian Bases＝DB的ビュー）の操作 |
| `json-canvas` | `.canvas`（JSON Canvas）の作成・編集 |
| `obsidian-cli` | Obsidian CLI 経由でVaultを操作（※CLI本体は任意の追加導入） |
| `defuddle` | WebページをきれいなMarkdownに抽出して取り込み |

Agent Skills 仕様準拠のため、Claude Code でそのまま利用可能。

---

## 事前準備（両PC共通・1回ずつ）

1. **Git for Windows** を導入（`winget install Git.Git`）。
2. **Node.js**（`npx` を使うため。`winget install OpenJS.NodeJS.LTS`）。
3. **Obsidian** 本体を導入（`winget install Obsidian.Obsidian`）。
4. **Claude Code** は両PCに導入済みの前提。
5. GitHubの認証（HTTPSなら Git Credential Manager が初回pushで案内。SSH派はSSH鍵を登録）。

---

## STEP 0: GitHubにプライベートリポジトリを作る（1回）

1. GitHub で **New repository** → 名前例 `obsidian-vault` → **Private** を選択 → 空で作成
   （README/.gitignore は付けない＝後でローカルから push するため）。
2. 表示される `https://github.com/<あなた>/obsidian-vault.git` を控える。

> 希望があれば、このリポジトリ作成はパリス側（GitHub連携）で代行も可能です。

---

## STEP 1: メインノートPC（イルサ）でVaultを新規作成して初期化

PowerShell を開いて、Vaultを置きたい場所で実行（例 `C:\Users\<you>\Obsidian\vault`）。

```powershell
# 1) Vaultフォルダを作成
mkdir $HOME\Obsidian\vault
cd $HOME\Obsidian\vault

# 2) Obsidianで「このフォルダをVaultとして開く」を一度実行 → .obsidian が生成される
#    （Obsidian → Open folder as vault → 上記フォルダを選択）

# 3) Gitリポジトリ化
git init
git branch -M main
```

### obsidian-skills を Vault に同梱（`.claude/skills` へ）

```powershell
# 公式リポジトリを一時取得して、skills 本体だけVaultの .claude/skills へコピー
git clone https://github.com/kepano/obsidian-skills.git $env:TEMP\obsidian-skills
New-Item -ItemType Directory -Force -Path .\.claude\skills | Out-Null
Copy-Item -Recurse -Force $env:TEMP\obsidian-skills\skills\* .\.claude\skills\
Remove-Item -Recurse -Force $env:TEMP\obsidian-skills
```

> 代替: `npx skills add https://github.com/kepano/obsidian-skills` でも導入可。
> ただし**Vaultと一緒にGit同期したい**ので、本手順では Vault直下の `.claude/skills` に置くのが要点。

### `.gitignore`（同期の競合と肥大化を防ぐ）

```powershell
@"
# Obsidianの端末ローカル状態（端末ごとに違う＝同期で競合する）
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache
.obsidian/.DS_Store

# ゴミ箱・OSファイル
.trash/
.DS_Store
Thumbs.db

# obsidian-skills導入時の一時物
.claude/skills/**/.git
"@ | Set-Content -Encoding UTF8 .gitignore
```

> `.obsidian/` の**設定（plugins, themes, app.json等）は同期したい**ので除外しない。
> 端末固有の `workspace.json` だけ除外するのがコツ。

### 初回コミット＆push

```powershell
git add -A
git commit -m "init: Obsidian vault + obsidian-skills"
git remote add origin https://github.com/<あなた>/obsidian-vault.git
git push -u origin main
```

---

## STEP 2: 常時機能PC（パリス）でクローンしてVaultとして開く

```powershell
cd $HOME\Obsidian
git clone https://github.com/<あなた>/obsidian-vault.git vault
```

- Obsidian を開き **Open folder as vault** → `C:\Users\<you>\Obsidian\vault` を選択。
- これで `.claude/skills`（obsidian-skills）も込みで両PCに揃う。

---

## STEP 3: 自動同期（Obsidian Git プラグイン）

手動 `git pull/push` でも回せるが、**両PCにObsidian Gitを入れて自動化**すると事故が減る。

1. Obsidian → 設定 → コミュニティプラグイン → **Obsidian Git** を検索して導入・有効化。
2. プラグイン設定の推奨値:
   - **Vault backup interval (minutes)**: `10`（10分ごとに自動コミット＆push）
   - **Pull updates on startup**: ON（起動時に必ず最新を取り込む）
   - **Pull changes before push**: ON（push前にpull＝競合を先に検知）
   - **Commit message**: `vault backup: {{date}}` 等
3. 両PCで同じ設定にする。

> **運用のコツ（重要）**: 片方で編集を始める前に、相手の自動pushが取り込まれている状態にする。
> 「起動時pull ON」「終了前にしばらく置いてpushを完了させる」を守れば、同じノートを同時刻に
> 両PCで触らない限りまず競合しない。

---

## STEP 4: Claude Code から obsidian-skills を使う

各PCの Claude Code を **Vaultフォルダ（リポジトリのルート）で起動**すると、`.claude/skills` が
プロジェクトスキルとして認識される。

- 例:「このVaultの今週のデイリーノートを要約して `Weekly/2026-W27.md` に書いて」
- 例:「Drive調査レポートを `[[物件/姫路A]]` から相互リンクして整理」
- 例:「このWebページを defuddle で取り込んで `Clippings/` に保存」

`obsidian-cli` スキルだけは CLI本体が必要になる場合がある（無くても他4スキルは動作）。
必要になったら本体導入は別途行う（各スキルの `SKILL.md` 参照）。

---

## 競合・トラブル時

- **競合（conflict）が出たら**: 慌てず該当ノートを開き、`<<<<<<<` `=======` `>>>>>>>` の
  マーカー部分を手で統合 → `git add` → `git commit`。Obsidian Git の "Resolve" 表示にも従う。
- **同じノートを両PCで同時編集しない**のが最大の予防策。常時機能PC側は基本「読み・追記」中心、
  本格編集はメインノートPC、のように役割を分けると安全。
- 画像など大容量を扱うなら将来 **Git LFS** の導入を検討（初期は不要）。

---

## このworkspace（秘書ハブ）との関係

- 秘書ハブ＝**AI同士の連携**用メッセージボックス（handoff）。
- Obsidian Vault＝**情報の集約・蓄積**先（ノート/Canvas/Bases）。
- 役割が違うので**別リポジトリ**として運用するのが素直。必要なら handoff 経由で
  「Vaultのここを更新して」とイルサ↔パリスで依頼し合える。
