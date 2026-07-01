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

## 運用計画（確定版 2026-07-01）

### 基本方針
- **処理主体**: 当面 **メインPCで福永さんが手動**。プラグインはメインPCのみ導入（常時機能PCは
  ノート同期のみで参照可。処理させたくなったら `/plugin install arscontexta@agenticnotetaking` を追加）。
- **モデル**: `/抽出` `/一括処理` など重い処理は **Sonnet**（レート枠回避）。設計判断・`/architect`
  は必要に応じ **Opus**。切替は `/model`。
- **自動化・qmd**: 運用が安定してから導入（Cowork夜間メンテ／qmd意味検索。`.mcp.json`配置済み）。

### 定期リズム
- **日次（Record）**: 会議メモ・意思決定・物件観察・調査メモを `受信箱/` に投下（記録のみ）。
- **週1〜2回（Reduce→Reflect）**: `/抽出`→`/紐付け` で知見化＆自動リンク。
- **週末（Verify）**: `/health` で孤立/スキーマ点検、必要に応じ `/更新`。
- **月次（Rethink）**: 本人がノートを目視レビュー（認知外注の防止）＋`/振り返り`。

### 初動ランブック（9本のChatGPT MDを早めに全消化）
1. 9本のMDを Vault の `受信箱/` に配置（未配置ならコピー/移動）。
2. メインPCのVaultで `claude` 起動 → `/model` で **Sonnet**。
3. `/一括処理 受信箱/[1本目]` → 生成ノートの**粒度・リンクを確認**（キャリブレーション）。
4. 問題なければ 2〜9本目を順に `/一括処理`（**1本ずつ**。Rate limit が出たら1〜2分休んで再開）。
5. 全部済んだら `/紐付け`（全体リンク）→ `/health` → ざっと目視レビュー。
6. Obsidian Git が自動でコミット＆push → 常時機能PCにも反映。

> ⚠️ 「早く全部」でも **1本ずつ**が安全（並列一括は瞬間レートに当たりやすい）。`/抽出` は
> ノイズを自動スキップするので、量を入れても"収集家の誤謬"はある程度抑制される。
