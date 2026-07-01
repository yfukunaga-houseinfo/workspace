# arscontexta セカンドブレイン 導入と運用

Obsidian Vault（`obsidian-vault`）を、AIが「ノートを勝手に繋いで育てる」セカンドブレインにするための
**arscontexta**（Claude Codeプラグイン／`agenticnotetaking/arscontexta`）の導入記録と運用計画。

- 前提: `docs/obsidian-multi-device-sync.md`（Git同期＋obsidian-skills）が完了していること。
- arscontextaはVault内に `self/ notes/(ノート) ops/ 受信箱/ アーカイブ/` を生成し、Git同期で両PCに展開される。
- 会話から「あなた専用の知識システム」を設計・生成するのが特徴（プリセット流用ではない）。

---

## 導入記録（2026-07-01 実施・メインPC）

環境: Windows / Claude Code 2.1.81 / Obsidian Vault = `C:\Users\fkng\Documents\作業フォルダ\Obsidian\vault`

### 前提ツール
- Claude Code v1.0.33+（実績 2.1.81）
- ripgrep（`winget install BurntSushi.ripgrep.MSVC`）
- tree（Windows標準）
- （任意・後で）qmd 意味検索: `npm install -g @tobilu/qmd`

### インストール手順
```
# VaultルートでClaude Codeを起動（重要: 生成物をVault内=同期対象に作るため）
cd "C:\Users\fkng\Documents\作業フォルダ\Obsidian\vault"
claude

# Claude Code内で
/plugin marketplace add agenticnotetaking/arscontexta
/plugin install arscontexta@agenticnotetaking
/reload-plugins            # 有効化（"Unknown skill" が出たら再起動）
/arscontexta:setup         # 20分の対話で専用システムを設計・生成
```

### つまずきポイントと対処（実績）
- **401 authentication_error** → `/login`（Claude Max / Organization アカウント）。
- **Rate limit reached（setupだけ即失敗）** → 使用量に余裕があっても、Opus 1Mの重い一括処理が
  「1分あたりのトークン枠」を超えるのが原因。**`/model` でSonnetに切替**すると通る。
- **ホームディレクトリで起動してしまう** → 必ず **Vaultルートで `claude`** を起動する。
- **SessionStart hook error** → arscontextaのフックが `.sh`（bash）でWindowsでは動かない。
  ただし auto-commit は Obsidian Git が肩代わりするため実害なし（表示上の問題）。

### 生成されたシステム
- 三層構造: `self/`（人格・方針）/ `notes/`＝`ノート/`（知識グラフ本体）/ `ops/`（運用状態）
- 初期MOC（地図）7本＋6事業領域の骨格（宿泊/建築設計/IT/財務/保育/コンテンツ資産）
- スキル16本: 抽出 / 紐付け / 更新 / 確認 / 検証 / 取込 / 処理エンジン / 一括処理 /
  タスク管理 / 統計 / グラフ分析 / 次の行動 / 学習 / 記録 / 振り返り / 再構築
- フック4本 / クエリ5本（施設別ノート密度・IT案件進捗・孤立ノート検出 ほか）
- 同期: Obsidian Git が自動コミット＆pushし、常時機能PCへ展開される

---

## 6R パイプライン（処理の背骨）

コーネル式ノートの拡張。inboxに素材を置き、順に回すとグラフが育つ。

| フェーズ | 役割 | コマンド |
|---|---|---|
| Record | ゼロ摩擦の記録（受信箱に置く） | 手入力 |
| Reduce | 素材から知見を抽出 | `/抽出 [source]` |
| Reflect | ノート間の接続を発見 | `/紐付け` |
| Reweave | 古いノートを新知見で更新 | `/更新` |
| Verify | 品質・スキーマ・リンク検証 | `/確認` `/health` |
| Rethink | 前提を問い直す | `/振り返り` `/記録` |

---

## 4つの高リスク（arscontextaの警告＝運用ガードレール）
1. **収集家の誤謬** … 「全部取り込む」誘惑。抽出基準を厳密に＋受信箱にWIP上限。
2. **孤立ノート問題** … 接続（`[[ ]]`）を省くと二度と見つからない。紐付けは必須。
3. **認知外注** … AIが自律するほど人間の判断チェックが薄れる。月次で本人がノートを確認。
4. **生産性ポルノ** … システム整備に没頭しノートが増えない。**ノート作成:システム修正=8:2**。

---

## 運用計画（初期ドラフト — 実運用で更新）

> 本節は運用しながら詰める骨子。確定した手順はここに追記していく。

### モデル方針
- 重い処理（`/抽出` `/一括処理`）は **Sonnet**（レート枠回避）。
- 微妙な設計判断・`/architect` 等は必要に応じ **Opus**。切替は `/model`。

### 実行環境（重要）
- arscontextaの**コマンドはプラグインを入れたPCでのみ動く**。現状はメインPCのみ導入済み。
- 常時機能PC（パリス）でも処理させたい場合は、そのPCのClaude Codeにも
  `/plugin install arscontexta@agenticnotetaking` を入れる（ノート本体はGit同期で共有済み）。

### 初期タスク（優先）
- 9本のChatGPT知識MDを受信箱に置き、**優先度順に1件ずつ** `/抽出`（Sonnet）。
- 抽出→`/紐付け`→`/確認` を1サイクル回し、孤立を出さない。

### 定期リズム（案）
- 日次: 会議メモ・意思決定・物件観察を受信箱に投下（記録のみ）。
- 週次: `/抽出`でまとめて知見化 → `/紐付け` → `/health`。
- 月次: 本人がノートを目視レビュー（認知外注の防止）＋`/振り返り`。

### 将来
- Claude Cowork のスケジュールで夜間自動メンテ（原子化→リンク→グラフ更新）を検討。
- qmd 導入で意味検索を有効化（`.mcp.json` 配置済み）。
