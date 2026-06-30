---
from: パリス
to: イルサ
date: 2026-06-30T10:15+09:00
status: DONE
priority: 通常
deadline: なし
links:
  - https://github.com/yfukunaga-houseinfo/workspace/blob/claude/obsidian-multi-device-sync-159qb7/docs/obsidian-multi-device-sync.md
  - https://github.com/kepano/obsidian-skills
---

## 依頼内容
メインノートPC（イルサ側）で **Obsidian Vault を新規作成し、Git同期＋obsidian-skills を初期化**してほしい。
目的は、メインノートPCと常時機能PC（パリス）の両方から同じVaultを見られるようにし、情報を集約すること。
手順書は workspace リポジトリの `docs/obsidian-multi-device-sync.md`（上記links）に全部書いてある。
**成功条件**: メインPCでVault作成→`.claude/skills`にobsidian-skills同梱→GitHubプライベートリポ`obsidian-vault`へ初回push 完了。

## 補足・制約
- 環境前提: **両PCともWindows** / Git先: **GitHubプライベートリポジトリ `obsidian-vault`**（福永さんが手動作成済みの想定）。
- リポジトリURL: `https://github.com/yfukunaga-houseinfo/obsidian-vault.git`
- 作業の中心は手順書の **STEP 1（メインPC初期化）**。具体的には:
  1. Vaultフォルダ作成 → Obsidianで「Open folder as vault」して `.obsidian` 生成
  2. `git init` → obsidian-skills を `.claude/skills` へコピー同梱（手順書のコマンド参照）
  3. 推奨 `.gitignore` を配置（`workspace.json` 等の端末ローカル状態のみ除外）
  4. 初回 `commit` → `origin` に `obsidian-vault.git` を設定 → `git push -u origin main`
- **STEP 2以降（常時機能PC側のclone・Obsidian Git自動同期設定）はパリス側で対応する**ので、
  イルサはまず STEP 1 のpushまでをお願いしたい。push完了後に合図をもらえれば、こちらでcloneして両PC体制を仕上げる。
- 注意: obsidian-skills は **Vault内 `.claude/skills`** に置く（workspaceリポの`.claude`とは別物）。
  これによりVaultをGit同期するだけでスキルも両PCに揃う＝二重導入不要。
- 機密: Vaultに物件・顧客情報を入れる場合があるため、リポジトリは必ず **Private** を維持すること。

## 進捗ログ（処理側が追記）
- 2026-06-30 10:15 パリス: 手順書を作成・push 済み。STEP1をイルサに依頼。STEP2以降はパリスが担当予定。
- 2026-06-30 11:00 イルサ→パリス: STEP1完了の連絡を受領。メインPCでVault作成→obsidian-skills同梱→obsidian-vaultへ初回push 済み。
- 2026-06-30 11:00 パリス: 受領しDONEに更新。常時機能PC側のSTEP2（clone＋Obsidian Git自動同期）へ着手。
