# join-pdf

2つの PDF を **同じ用紙サイズ（ページ寸法）** に揃えてから、先頭から順に1本に結合します。元の縦横比は保ち、枠内に収まるよう均等スケールします（はみ出しは余白で埋まります）。

## 必要環境

- Python 3.9 以降を想定
- 依存: [PyMuPDF](https://pymupdf.readthedocs.io/)（`pymupdf`）

## セットアップ

```bash
cd join-pdf
pip install -r requirements.txt
```

## 使い方

```bash
python3 main.py <1つ目のPDF> <2つ目のPDF> [-o 出力.pdf] [サイズ指定]
```

### 出力先

| オプション | 説明 |
|------------|------|
| `-o` / `--output` | 出力ファイルパス（省略時は `merged.pdf`） |

### 用紙サイズ（どちらか一方）

**デフォルト**は **A4**（595×842 pt）です。

| オプション | 説明 |
|------------|------|
| `--size SPEC` | 全ページをこのサイズに揃える。下記プリセットまたは `幅x高さ`（ポイント） |
| `--match first` | 1つ目の PDF の **1ページ目** と同じ用紙サイズに揃える |
| `--match second` | 2つ目の PDF の **1ページ目** と同じ用紙サイズに揃える |

`--size` と `--match` は同時に指定できません。

#### `--size` の SPEC

- **プリセット**: `a4`（既定と同じ）, `a4landscape`, `a3`, `letter`
- **任意サイズ**: `幅x高さ`（72 dpi のポイント。例: `612x792`）

## 例

A4 に揃えて結合（出力名を指定）:

```bash
python3 main.py doc1.pdf doc2.pdf -o combined.pdf
```

Letter サイズに揃える:

```bash
python3 main.py doc1.pdf doc2.pdf -o out.pdf --size letter
```

2つ目の PDF の1ページ目と同じ用紙サイズに揃える:

```bash
python3 main.py doc1.pdf doc2.pdf -o out.pdf --match second
```

## 動作の補足

- 結合順は **1つ目の全ページ → 2つ目の全ページ** です。
- 各元ページは、指定した矩形内に **アスペクト比固定** で収められます。用紙比率が違う場合は上下または左右に余白が付きます。
- 元 PDF に書き込まれた **追記（注釈・フォーム入力欄の表示）は、結合時にページ内容として保持** されます。

## ヘルプ

```bash
python3 main.py -h
```
