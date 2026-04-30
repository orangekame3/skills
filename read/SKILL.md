---
name: read
description: arxiv論文のPDFを取得し、arqのsummary.mdを土台にnote.mdとして精読ノートを生成する。
argument-hint: "<arxiv ID (例: 2603.16203)>"
compatibility: Requires arq CLI, uv, marp, and mo
allowed-tools: WebFetch, Bash(arq *), Bash(curl *), Bash(mo *), Bash(marp *), Bash(mkdir *), Bash(ln *), Read, Write, Glob, Edit
---

# arxiv 論文リーディング

## 概要

arxiv ID を受け取り、arq の summary.md を土台にして、精読ノート（note.md）を arq 管理下に生成する。
summary.md の構造化された内容をベースに、PDF で補完し、個人的な所感を加える。

## 手順

### 1. 論文情報の取得

arq を使って論文の取得・サマリー生成・ローカル保存を行う。

#### 1a. 論文の取得・保存・サマリー生成

```bash
arq get --summarize $ARGUMENTS
```

これにより以下が `$ARQ_ROOT/arxiv.org/<category>/<id>/` に保存される：
- `paper.pdf` — 原文 PDF
- `paper_ja.pdf` — 日本語翻訳 PDF（Mac Studio で自動生成。取得直後は存在しない場合がある）
- `meta.json` — メタデータ
- `summary.md` — ar5iv HTML ベースの LLM 生成サマリー（図付き）
- `assets/` — サマリーに含まれる図

既に取得済みの場合、PDF・メタデータはスキップされる。
サマリーが未生成の場合は `arq summarize $ARGUMENTS` で個別生成できる。

取得・サマリー生成が完了したら、すぐに mo でサマリーを表示する：

```bash
arq view $ARGUMENTS --target arq
```

#### 1b. メタデータの取得

```bash
arq show --json $ARGUMENTS
```

タイトル・著者・アブストラクト・カテゴリ・PDF パスを JSON で取得できる。

### 2. summary.md の読み込み（土台）

```bash
arq show --summary $ARGUMENTS
```

サマリーには以下が含まれる：
- Overview → 「ひとことで言うと」の土台
- Background & Motivation → そのまま活用
- Method → そのまま活用（数式・図の参照付き）
- Key Results → 定量的な結果の土台
- Key Figures → 図のファイル名と説明
- Significance & Future Work → 議論セクションの土台

**summary.md の内容は note.md にコピーせず、参照しながら咀嚼した記述を書く。**

### 3. PDF 読み込み（補完）

サマリーだけでは不十分な場合（詳細な数式、図表の解釈、具体的な数値等）、PDF を直接読む。

```bash
arq path $ARGUMENTS
```

返されたパスを Read ツールで PDF を読み込む（長い場合はページ範囲を指定して分割読み込み）。

特に以下は PDF で確認すべき：
- 具体的な実験条件（量子ビット数、ショット数など）
- 表に含まれる定量的な数値
- サマリーで省略された手法の詳細

### 4. note.md の生成

arq 管理下の論文ディレクトリに `note.md` を生成する。

#### 4a. 保存先の確認

```bash
arq path $ARGUMENTS
```

返されたパスの親ディレクトリ（`dirname`）に `note.md` を保存する。

#### 4b. note.md のフォーマット

以下の形式で日本語にまとめる。**専門家向けだが読みやすい文体**で書く。
summary.md の内容を土台にしつつ、より咀嚼・補強した記述にする。

```markdown
# [論文タイトルの日本語訳]

> **原題**: 英語タイトル
> **著者**: 著者名
> **arxiv**: [ID](https://arxiv.org/abs/ID)
> **投稿日**: YYYY-MM-DD

---

## ひとことで言うと

この論文が何をしたのか、1-2文で端的に。
（summary.md の Overview を凝縮）

## 背景・モチベーション

- この研究が解こうとしている問題は何か
- 先行研究では何ができていて、何ができていなかったか
- なぜ今この研究が重要なのか
（summary.md の Background & Motivation を土台に、PDF で補強）

## 手法・アプローチ

- 具体的に何をどうやったのか
- 新しいアイデアの核心部分を噛み砕いて説明
- 図や数式の要点があれば言及（数式は KaTeX 記法で記載）
（summary.md の Method を土台に、PDF の数式・図表で補強）

## 主要な結果

- 定量的な結果（数値・性能指標）
- 定性的な発見
- 先行研究との比較
（summary.md の Key Results + PDF の表・図から具体的な数値を抽出）

## 議論・インパクト

- この結果が意味すること
- 超伝導量子コンピュータ開発への影響（関連する場合）
- 限界・今後の課題
（summary.md の Significance & Future Work を土台に）

## 個人的な所感

- 自分の仕事（超伝導QCのシステム開発）との関連性
- 実装や実験への示唆
- フォローすべきポイント
（これは summary.md にはない。独自の視点で書く）
```

#### 4c. 保存

```bash
# 保存先パスの取得
PAPER_DIR=$(dirname $(arq path $ARGUMENTS))
# note.md を保存
# Write ツールで $PAPER_DIR/note.md に書き込む
```

### 5. life/reads/ へのシンボリックリンク

note.md の実体は arq 管理下に置くが、life/reads/ からも参照できるようにシンボリックリンクを作成する。

```bash
PAPER_DIR=$(dirname $(arq path $ARGUMENTS))
ln -sfn $PAPER_DIR/note.md reads/YYYY-MM-DD_$ARGUMENTS.md
```

これにより：
- 実体は arq 管理下（1箇所で管理）
- life/reads/ からも従来通りアクセス可能
- reads/README.md のインデックスも引き続き機能

### 6. トレンドレポートへのリンク追記

読了した論文がトレンドレポート (`trends/quant-ph/YYYY-MM-DD.md`) に掲載されている場合、
該当エントリに読了レポートへのリンクを追記する。

```markdown
- **📖 読了**: [読了レポート](../../reads/YYYY-MM-DD_ARXIV_ID.md)
```

概要の直後に上記の行を追加すること。

### 7. README の更新

`reads/README.md` の Index テーブルの先頭行（ヘッダ直後）に新しいエントリを追加する。

```markdown
| YYYY-MM-DD | [ARXIV_ID](YYYY-MM-DD_ARXIV_ID.md) | タイトル |
```

また、`trends/README.md` の該当日の「読了論文」列にもリンクを追加する。該当日がない場合は追加不要。

### 8. 既知 ID の登録

`arq get` で PDF・メタデータは arq が管理する。
加えて、トレンドの重複排除用に `data/known_arxiv_ids.txt` にも追記する:

```bash
echo "$ARGUMENTS" >> data/known_arxiv_ids.txt
sort -u data/known_arxiv_ids.txt -o data/known_arxiv_ids.txt
```

### 9. mo でノートを開く

保存完了後、ノートを mo で開く:

```bash
mo reads/YYYY-MM-DD_$ARGUMENTS.md --target reads --no-open
```

mo サーバーが起動していれば既存セッションに追加される。

### 10. スライドの生成

ノートの保存後、発表用の Marp スライドを自動生成する。
`/slide $ARGUMENTS` スキルの手順に従って実行する。

具体的には:
1. `slides/$ARGUMENTS/` ディレクトリを作成し、arq の assets/ をシンボリックリンク
2. `slides/templates/white.css` のテーマ CSS を使用
3. note.md + arq サマリー + 図からスライドを生成
4. `marp` で PDF をビルド
5. PDF のパスを報告
