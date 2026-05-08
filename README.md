# toolhub

PDF と画像を扱う小さな CLI ツールを集めたモノレポです。各ツールは独立したフォルダに配置されており、それぞれ自分の `main.py`・`requirements.txt`・`README.md` を持ちます。

## 収録ツール

| ツール | 概要 | 依存 |
|--------|------|------|
| [`join-pdf`](./join-pdf) | 2つの PDF を **同じ用紙サイズに揃えて結合** する | PyMuPDF |
| [`flatten-pdf`](./flatten-pdf) | PDF を **編集不可（フラット化）** にする | PyMuPDF |
| [`pdf2img`](./pdf2img) | PDF の各ページを **画像（PNG / JPEG）** にエクスポート | PyMuPDF |
| [`img2pdf`](./img2pdf) | 複数の画像を **1つの PDF** にまとめる | Pillow |

詳細とオプションは各ツールの `README.md` を参照してください。

## 必要環境

- Python 3.9 以降を想定
- 各ツールは **独立した `requirements.txt`** を持っています（不要なツールの依存はインストールしなくて構いません）

## 使い方の基本

各ツールは同じ流れで使えます。

```bash
cd <ツール名>            # 例: cd join-pdf
pip install -r requirements.txt
python3 main.py -h       # ヘルプを確認
python3 main.py ...      # 実行
```

### 例

```bash
# 2つの PDF を A4 で結合
cd join-pdf
pip install -r requirements.txt
python3 main.py a.pdf b.pdf -o merged.pdf

# その PDF を編集不可にする
cd ../flatten-pdf
pip install -r requirements.txt
python3 main.py ../join-pdf/merged.pdf -o merged.flat.pdf

# PDF の各ページを 300 DPI の PNG に
cd ../pdf2img
pip install -r requirements.txt
python3 main.py ../join-pdf/merged.pdf --dpi 300

# 画像をまとめて 1 つの PDF に
cd ../img2pdf
pip install -r requirements.txt
python3 main.py img/ -o output.pdf
```

## 組み合わせ例

- **結合 → 編集不可化**: `join-pdf` → `flatten-pdf`
- **PDF → 画像 → 別の PDF**: `pdf2img` → 画像加工 → `img2pdf`

## ディレクトリ構成

```
toolhub/
├── README.md
├── flatten-pdf/   # PDF を編集不可（フラット化）
├── img2pdf/       # 画像 → PDF
├── join-pdf/      # PDF 結合（用紙サイズ統一）
└── pdf2img/       # PDF → 画像
```
