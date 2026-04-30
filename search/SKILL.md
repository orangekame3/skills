---
name: search
description: 特定テーマで arxiv・Web を横断検索し、重要論文をピックアップする。トレンド(日次新着)と異なり、過去論文を含めた自由探索。
argument-hint: "<検索テーマ（日本語 or 英語）>"
compatibility: Requires curl and arq CLI
---

# 論文自由探索

## 概要

特定のテーマ・キーワードで arxiv と Web を横断的に検索し、過去の重要論文を含めて探索する。
`/trend` が日次新着の定点観測なのに対し、`/search` はテーマ駆動の深掘り探索。

## 手順

### 1. 検索テーマの整理

`$ARGUMENTS` から以下を決定する：

- **英語キーワード**: arxiv 検索用（複数パターン）
- **検索カテゴリ**: デフォルトは `quant-ph`。テーマによっては `cs.AI`, `cs.LG`, `cond-mat` 等も対象に
- **探索の狙い**: 何を知りたいのか（手法？実装？比較？）

### 2. 多角的な検索

以下を**並列ではなく順次**実行する。各リクエスト間に `sleep 5` を挟むこと。

#### 2a. arxiv API（relevance ソート）

テーマに合わせた検索クエリを 2-3 パターン組み、各 10 件を relevance ソートで取得。

```bash
curl -sL -w "\nHTTP_CODE: %{http_code}" 'https://export.arxiv.org/api/query?search_query=cat:quant-ph+AND+all:%22KEYWORD1%22+AND+all:%22KEYWORD2%22&start=0&max_results=10&sortBy=relevance&sortOrder=descending' 2>&1
```

- レート制限時は exponential backoff（10s → 30s → スキップ）
- 必要に応じて `submittedDate` ソートでも検索し、最新の動向も捕捉

#### 2b. Web 検索

arxiv API で拾えない論文や関連情報を補完する。

```
WebSearch: arxiv "<KEYWORD1>" "<KEYWORD2>" quantum 2025 2026
```

- arxiv.org にドメインを限定した検索と、限定しない広い検索の両方を試す
- レビュー論文、チュートリアル、ブログ記事なども有用な場合は拾う

#### 2c. 既知論文との突き合わせ・重複除外

2段階で既知チェックを行う:

1. **精読済みチェック（バッチ）**: 候補 ID をまとめて `arq has` に渡し、精読済みの ID を一括で取得する
   ```bash
   # 候補IDを改行区切りで渡し、精読済みIDだけが出力される
   echo -e "2603.16203\n2601.19635\n2509.12949" | arq has -
   ```
2. **トレンド既出チェック**: `data/known_arxiv_ids.txt` に含まれるかを確認

精読済みの論文は「関連する既読論文」セクションで言及する。
`arq search` でテーマに関連する精読済み論文を探すこともできる:
```bash
arq search --id "surface code"   # テーマで精読済み論文を検索
```

精読済み論文にサマリーがある場合は `arq show --summary <id>` で要約を参照し、関連性の説明に活用する。

トレンド既出の論文はピックアップ対象から除外する（関連性が高いものは言及可）。

**レポート完了後、新たに掲載した全 arxiv ID を `data/known_arxiv_ids.txt` に追記する。**
**search の論文は arq には登録しない**（arq は精読する論文専用）。

```bash
# known_arxiv_ids.txt に追記
echo "<新規IDを1行1つ>" >> data/known_arxiv_ids.txt
sort -u data/known_arxiv_ids.txt -o data/known_arxiv_ids.txt
```

### 3. 出力フォーマット

```markdown
# 探索レポート: [テーマ]

> 検索日: YYYY-MM-DD
> キーワード: keyword1, keyword2, ...

## サマリー

このテーマの現状を 3-5 行で概観。

## 重要論文ピックアップ

### 1. [論文タイトル (日本語訳)]
- **原題**: 英語タイトル
- **著者**: 著者名
- **arxiv ID**: ID (リンク付き)
- **発表日**: YYYY-MM-DD
- **概要**: 3-4 行の日本語要約
- **なぜ重要か**: このテーマにおける位置づけ
- **既読関連**: (あれば既読レポートへのリンク)

### 2. ...

(5-10 本程度をピックアップ)

## 関連する既読論文

既に精読済みの関連論文をリストアップ。

## 次のアクション候補

- 精読すべき論文の推薦（優先度付き）
- 関連テーマへの展開提案
```

### 4. レポートの保存

以下のパスに保存する:

```
searches/YYYY-MM-DD_<テーマのスラッグ>.md
```

ディレクトリが存在しない場合は作成すること。
テーマのスラッグは英語・ケバブケースで簡潔に（例: `calibration-optimization`, `llm-quantum`）。

### 5. README の更新

`searches/README.md` が存在する場合、Index テーブルの先頭行に新しいエントリを追加する。
存在しない場合は以下のフォーマットで作成する：

```markdown
# Searches

テーマ駆動の論文自由探索レポート。

## Index

| 日付 | テーマ | レポート |
|---|---|---|
| YYYY-MM-DD | テーマ名 | [リンク](ファイル名) |
```
