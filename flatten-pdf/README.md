# flatten-pdf

PDF を **編集不可（フラット化）** にするツール。

- 注釈（ハイライト・フリーテキストなど）を **ページ内容に焼き付け**
- フォーム入力欄（テキストフィールド・チェックボックス等）を **見た目のままページ内容に焼き付け**、`/AcroForm` をカタログから外して **「フォームPDF」扱いをやめさせる**
- 必要なら **画像化** モードでページを再レンダリング（最終手段。テキスト選択不可になります）

## 必要環境

- Python 3.9 以降を想定
- 依存: [PyMuPDF](https://pymupdf.readthedocs.io/)（`pymupdf`）

## セットアップ

```bash
cd flatten-pdf
pip install -r requirements.txt
```

## 使い方

```bash
python3 main.py <入力PDF> [-o 出力.pdf]
```

主なオプション:

| オプション | 説明 |
|------------|------|
| `-o` / `--output` | 出力先（既定: `<入力名>.flat.pdf`） |
| `--keep-annots` | 注釈を焼き付けない |
| `--keep-widgets` | フォームウィジェットを焼き付けない／`/AcroForm` を残す |
| `--rasterize [DPI]` | 各ページを画像化して PDF を再構成（既定 200 DPI、テキスト選択不可） |

## 例

通常のフラット化:

```bash
python3 main.py 入力.pdf -o 出力.pdf
```

それでもビューアが「フォーム」「編集」表示を出す場合は画像化:

```bash
python3 main.py 入力.pdf -o 出力.pdf --rasterize 200
```

`../join-pdf` で結合した直後に編集不可化:

```bash
python3 ../join-pdf/main.py a.pdf b.pdf -o merged.pdf
python3 main.py merged.pdf -o merged.flat.pdf
```

## 動作の補足

- フラット化後は **編集可能なフォーム** や **電子署名の有効性** など、PDF としての「生の」機能は期待できません（見た目優先）。
- `--rasterize` モードは見た目を完全に固定できますが、**テキスト選択・検索** はできなくなります。

## ヘルプ

```bash
python3 main.py -h
```
