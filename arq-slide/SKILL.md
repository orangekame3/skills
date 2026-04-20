---
name: arq-slide
description: 精読済み論文のMarpスライドを生成する。reads/ の精読レポートと arq のサマリー・図を組み合わせて発表用スライドを作成。
argument-hint: "<arxiv ID (例: 2603.29439)>"
compatibility: Requires arq CLI and marp CLI
allowed-tools: WebFetch, Bash(arq *), Bash(marp *), Bash(ln *), Bash(mkdir *), Bash(cp *), Bash(cat *), Read, Write, Glob, Edit
---

# 論文スライド生成

## 概要

精読済み論文（`reads/` にレポートがあるもの）から、Marp 形式の発表用スライドを生成する。

## 手順

### 1. 精読レポートの確認

`reads/` ディレクトリから該当する arxiv ID のレポートを検索する。

```
reads/*_$ARGUMENTS.md
```

レポートが見つからない場合は、先に `/arq-read $ARGUMENTS` でレポートを生成するよう案内する。

### 2. 情報の収集

以下のソースを読み込む:

#### 2a. 精読レポート（主ソース）

精読レポートの全セクションを読み込む。特に以下が重要:
- ひとことで言うと → タイトルスライドのサブタイトルに
- 背景・モチベーション → Background セクションに
- 手法・アプローチ → Method セクションに（複数スライドに分割）
- 主要な結果 → Results セクションに
- 議論・インパクト → Discussion セクションに
- 個人的な所感 → まとめスライドに反映

#### 2b. arq サマリー

```bash
arq show --summary $ARGUMENTS
```

サマリーには構造化された要約と図への参照が含まれる。
精読レポートにない情報（図の説明など）を補完する。

#### 2c. arq メタデータ

```bash
arq show --json $ARGUMENTS
```

タイトル・著者・日付・カテゴリなどを取得。

#### 2d. 図のリンク

```bash
arq path $ARGUMENTS
```

返されたパスの親ディレクトリに `assets/` がある。
スライドから相対パスで参照できるようにシンボリックリンクを作成する。

### 3. スライドのスキャフォールド

出力ディレクトリを作成し、図のアセットをリンクする:

```bash
mkdir -p slides/$ARGUMENTS
ln -sfn $(dirname $(arq path $ARGUMENTS))/assets slides/$ARGUMENTS/assets
```

### 4. テンプレートの読み込み

テンプレートを読み込む:
- `slides/templates/paper-review.md` — スライド構造のテンプレート
- `slides/templates/kanagawa.css` — Kanagawa テーマの CSS

### 5. スライドの生成

テンプレートの構造に従い、収集した情報からスライドを生成する。

#### スライド構成の基本方針

- **1スライド1メッセージ**: 各スライドで伝えたいことは1つに絞る
- **箇条書きは3-5個**: 多すぎると読めない
- **数式は KaTeX**: `$O(n^2)$`, `$T_1$` など
- **図の活用**: arq の `assets/` にある論文の図を積極的に使う（後述の図レイアウトガイドを参照）
- **太字で強調**: 定量的な結果は `**19.5×**` のように太字にする
- **テーブルの活用**: 比較は表形式が効果的

#### はみ出し防止ルール（重要）

Marp はコンテンツが多くても自動縮小しない。はみ出しを防ぐために以下を厳守する。

**テキスト:**
- 長いタイトルは `<!-- fit -->` を使う: `# <!-- fit --> 長いタイトル`
- 通常スライドの本文は **10行以内** に収める
- `bg right` / `bg left` 使用時はテキスト側 **6行以内**
- h3 (###) のセクションが3つ以上ある場合はスライドを分割する

**図:**
- インライン図は必ずサイズ指定する: `![w:800](path)` or `![w:700 h:400](path)`
- `bg` 指定には必ず `contain` を付ける（`cover` だと切れる）
- 全面表示の場合は `![w:950 center](path)` を上限とする
- 左右分割で図が複雑な場合は `bg right:55%` のように図側を広げる

**テーブル:**
- 列は **4列以内** にする（5列以上ははみ出す）
- セル内テキストは短く（1セル20文字以内が目安）
- 行数は **6行以内**（ヘッダ含む）。それ以上は分割

**divider スライド:**
- h2 テキストは **15文字以内** にする（長いと改行されて崩れる）

**lead スライド:**
- タイトルが長い場合は `<!-- fit -->` を必ず使う
- サブタイトル（h2）は1行に収める

#### 図のレイアウトガイド

arq のサマリー（`summary.md`）に図のファイル名と説明がある。これを読んで各図の内容を把握し、適切なスライドに配置する。

**レイアウトパターン（優先度順）:**

```markdown
<!-- パターン1: 左右分割（図+説明） — 最も推奨 -->
![bg right:50% contain](assets/x4.png)
# 手法の概要
- ADC: デコヒーレンス誤り
- SDC: ゲートエラー
- SPAM: 初期化・測定

<!-- パターン2: 図を全面表示して上にテキスト -->
![bg contain opacity:0.15](assets/x1.png)
# 超伝導量子ビットの誤差源
主要な誤差と QEC シンドロームとの関係

<!-- パターン3: 図のみのスライド（キャプション付き） -->
![w:900 center](assets/x2.png)
*相関行列の比較: Experiment vs SI1000 vs PAEMS*

<!-- パターン4: 2枚の図を左右に並べて比較 -->
![bg left:50% contain](assets/x2.png)
![bg right:50% contain](assets/x3.png)
```

**使い分けの目安:**
- 概念図・回路図（x1, x4, x5）→ パターン1（左右分割）で説明と並べる
- 結果の図（x2, x3）→ パターン3（大きく見せる）or パターン4（比較）
- 図が複雑で細部が重要 → パターン3 で `w:900` 以上にする
- 図はあくまで補助 → パターン2 で背景に薄く敷く

**注意:**
- `bg right` / `bg left` を使うとテキスト領域が半分になるので、箇条書きは3個以内にする
- `contain` は必ず付ける（`cover` だと図が切れる）
- 図のキャプションは `*イタリック*` で図の下に書く

#### CSS の埋め込み

テンプレートの `{{KANAGAWA_CSS}}` 部分に `kanagawa.css` の内容を埋め込む。
Marp では `style:` フロントマター内に CSS を直接記述する必要があるため。

#### スライドクラスの使い分け

- `<!-- _class: lead -->` — タイトルスライド、Thank you
- `<!-- _class: divider -->` — セクション区切り（BACKGROUND, METHOD, RESULTS, DISCUSSION）
- `<!-- _class: impact -->` — インパクトのある1行メッセージ
- （クラスなし） — 通常のコンテンツスライド

### 6. 保存

以下のパスに保存する:

```
slides/$ARGUMENTS/slides.md
```

### 7. PDF ビルド

```bash
marp slides/$ARGUMENTS/slides.md -o slides/$ARGUMENTS/slides.pdf --allow-local-files
```

ビルドが成功したら PDF のパスを報告する。

### 8. プレビュー

```bash
open slides/$ARGUMENTS/slides.pdf
```

## 注意事項

- スライドの内容は精読レポートと arq サマリーに基づく。論文に記載のない情報を追加しない
- 図は arq の assets/ から参照する。スライド側にコピーしない（シンボリックリンクで参照）
- CSS テーマはユーザーの好みに応じて kanagawa（ダーク）を使用する。ユーザーが「白テーマ」と言った場合は別のテーマ CSS を用意する
