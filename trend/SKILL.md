---
name: trend
description: arxiv quant-ph (量子コンピュータ・量子物理) の最新論文トレンドを収集・要約する。情報収集や研究動向の把握に使う。
argument-hint: "[キーワード(省略可)]"
compatibility: Requires uv, curl, and arq CLI
allowed-tools: WebFetch, Bash(curl *), Bash(uv run *), Bash(arq *), Bash(mo *), Read, Write, Glob, Agent
---

# arxiv quant-ph トレンド収集

## 概要

arxiv の quant-ph (Quantum Physics) カテゴリから最新の論文を取得し、トレンドを日本語で要約する。

**重要: レポートの全文（セクションタイトル、概要、全体傾向、コメント等）はすべて日本語で記述すること。英語で書くのは原題（Original Title）と著者名のみ。**

## スクリプト

このスキルに同梱されたスクリプトを使用する。スクリプトはこの SKILL.md と同じディレクトリの `scripts/` にある。

| スクリプト | 役割 |
|---|---|
| `scripts/arxiv_pipeline.py` | **メインスクリプト**: fetch → parse → merge → arq check を一括実行 |
| `scripts/arxiv_fetch.py` | arxiv API からの論文取得（レート制限・リトライ・RSS フォールバック込み） |
| `scripts/arxiv_parse.py` | XML → JSON 変換 |
| `scripts/arxiv_merge.py` | 複数 JSON の統合・既知ID除外・興味領域カテゴリ分け |

スクリプトの実行時は、この SKILL.md が配置されているディレクトリからの相対パスで `scripts/` を参照すること。

## 手順

### 0. 週末チェック

RSS フィードは **土曜・日曜はデータが空** になる（arxiv の skipDays 設定）。
土日に実行する場合、RSS フォールバックでもデータが取得できない可能性がある。
その場合は「本日は週末のため新着論文なし」と報告して終了する。

### 1. パイプライン実行

`arxiv_pipeline.py` が fetch → parse → merge → arq check をすべて処理する。
`--known` には CWD（life リポジトリ）の `data/known_arxiv_ids.txt` のパスを渡す。

```bash
SKILL_DIR="$(dirname "$(readlink -f "$(grep -rl 'name: trend' ~/.claude/skills/*/SKILL.md 2>/dev/null | head -1)")" 2>/dev/null)"
uv run "$SKILL_DIR/scripts/arxiv_pipeline.py" --known data/known_arxiv_ids.txt
```

キーワード指定がある場合:
```bash
uv run "$SKILL_DIR/scripts/arxiv_pipeline.py" --known data/known_arxiv_ids.txt --keyword "$ARGUMENTS"
```

stdout にマニフェスト JSON が出力される:
```json
{
  "daily": "/tmp/arxiv_daily.json",
  "deep": "/tmp/arxiv_deep.json",
  "read_ids": ["2604.xxxxx"],
  "stats": { "new": 51, "total": 96, "deep_new": 3, "categories": {...} }
}
```

### 2. JSON データの構造

`/tmp/arxiv_daily.json` と `/tmp/arxiv_deep.json` は以下の形式:

```json
{
  "total_fetched": 96,
  "new_papers": 51,
  "categorized": { "superconducting": ["2604.xxxxx", ...], ... },
  "general": ["2604.yyyyy", ...],
  "papers": {
    "2604.xxxxx": {
      "id": "2604.xxxxx",
      "title": "...",
      "authors": ["..."],
      "summary": "...",
      "date": "2026-04-18",
      "interest_areas": ["superconducting", "calibration"]
    }
  }
}
```

- `categorized`: 興味領域ごとの論文 ID リスト
- `general`: どの興味領域にも分類されなかった論文 ID リスト
- `papers`: 全論文の詳細（ID をキーとする辞書）

### 3. レポート作成

`/tmp/arxiv_daily.json` と `/tmp/arxiv_deep.json` を読み、以下のフォーマットでレポートを作成する。
**興味領域のセクションを優先的に配置する。**
**JSON にはタイトル・著者・概要の英語原文が入っている。日本語訳・要約は自分で書くこと。**
**`read_ids` に含まれる論文には精読レポートへのリンクを付記する。**

```markdown
# quant-ph トレンドレポート (YYYY-MM-DD)

## 全体傾向
- 今回取得した論文群から読み取れるトレンドを 3-5 点で箇条書き

---

## 超伝導量子コンピュータ・デバイス

#### 1. [論文タイトル (日本語訳)]
- **原題**: 英語タイトル
- **著者**: 著者名
- **arxiv ID**: ID (リンク付き)
- **概要**: 3-4 行の日本語要約。何が新しいのか、なぜ重要なのかを含める

## Surface Code / 量子誤り訂正

(同上フォーマット)

## システム・アーキテクチャ・クラウド

(同上フォーマット)

## キャリブレーション

(同上フォーマット)

## LLM・AI × 量子コンピュータ

(同上フォーマット)

---

## quant-ph 一般トレンド（注目論文）

(上記カテゴリに含まれない注目論文 上位3件)

---

## その他の論文一覧
| # | タイトル (日本語) | arxiv ID | キーワード |
|---|---|---|---|
| 1 | ... | ... | ... |

---

## 興味領域ピックアップ（過去の重要論文）

relevance ソートで取得した、日次トレンドには含まれない過去の重要論文。
各興味領域から 1-3 本をピックアップし、なぜ今読む価値があるかを添える。

### Surface Code 実証実験
#### 1. [論文タイトル (日本語訳)]
- **原題**: 英語タイトル
- **著者**: 著者名
- **arxiv ID**: ID (リンク付き)
- **発表日**: YYYY-MM-DD
- **概要**: 3-4 行の日本語要約
- **今読む価値**: なぜこの論文が現在の文脈で重要か

### 超伝導キャリブレーション
(同上フォーマット)

### クラウド量子コンピュータ / システムアーキテクチャ
(同上フォーマット)

### 量子誤り訂正デコーダ
(同上フォーマット)

### LLM・エージェント × キャリブレーション自動化
(同上フォーマット)
```

### 4. 保存・更新

#### 4a. レポートの保存

```
trends/quant-ph/YYYY-MM-DD.md
```

ディレクトリが存在しない場合は作成すること。

#### 4b. 既知 ID の更新

レポートに掲載した全 arxiv ID を `data/known_arxiv_ids.txt` に追記する（重複排除用）。
**トレンドの論文は arq には登録しない**（arq は精読する論文専用）。

```bash
# レポートに掲載した ID を known_arxiv_ids.txt に追記
echo "<新規IDを1行1つ>" >> data/known_arxiv_ids.txt
sort -u data/known_arxiv_ids.txt -o data/known_arxiv_ids.txt
```

#### 4c. README の更新

`trends/README.md` の quant-ph テーブルの先頭行（ヘッダ直後）に新しいエントリを追加する。

```markdown
| [YYYY-MM-DD](quant-ph/YYYY-MM-DD.md) | トレンド要約キーワード | — |
```

「読了論文」列は初期値 `—` とし、精読時に更新される。

#### 4d. レポートをブラウザで表示

作成したレポートを `mo` で開く。

```bash
mo trends/quant-ph/YYYY-MM-DD.md --target trend
```
