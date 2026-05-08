# compress-pdf

PDF の **容量** と **ページ内画像の推定 DPI** を確認し、必要に応じて **容量圧縮** します。

圧縮は次の優先順で動作します。

- Ghostscript（`gs`）が使える: **目標 DPI で画像をダウンサンプル**（効果が大きい）
- Ghostscript がない: PDF を安全に **最適化保存**（ゴミ除去・圧縮。DPI は変わりません）

## 必要環境

- Python 3.9 以降を想定
- 依存: [PyMuPDF](https://pymupdf.readthedocs.io/)（`pymupdf`）
- （任意）Ghostscript: `gs` コマンド（DPI を下げる圧縮に必要）

## セットアップ

```bash
cd compress-pdf
pip install -r requirements.txt
```

## 使い方

### 容量・推定 DPI を確認

```bash
python3 main.py info input.pdf
```

### 用紙サイズを揃える（例: A4 = 595×842pt）

```bash
python3 main.py resize input.pdf -o output.a4.pdf --size a4
```

`--size` は `a4`, `a3`, `letter`, `a4landscape` または `幅x高さ`（ポイント）を指定できます。

### 圧縮（目標 DPI を指定）

```bash
python3 main.py compress input.pdf -o output.pdf --dpi 150
```

#### 圧縮プリセット（Ghostscript 使用時）

```bash
python3 main.py compress input.pdf -o output.pdf --preset ebook
```

利用可能: `screen`, `ebook`（既定）, `printer`, `prepress`, `default`

## ヘルプ

```bash
python3 main.py -h
python3 main.py info -h
python3 main.py compress -h
```
