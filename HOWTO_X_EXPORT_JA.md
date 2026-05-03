# Xポスト書き出しツールの使い方（日本語）

結論：**2つの `.py` をデスクトップに置くだけでは不十分**です。  
Python本体と必要パッケージのインストールが必要です。

## どちらを使う？

- `export_x_posts.py`
  - 公式X API版（`X_BEARER_TOKEN` 必須）
- `export_x_posts_snscrape.py`
  - 非公式スクレイピング版（APIトークン不要）

## 最短手順（macOS / Linux）

```bash
# 1) デスクトップへ移動
cd ~/Desktop

# 2) 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate

# 3) 必要ライブラリを入れる
pip install requests snscrape

# 4-A) API版を実行（トークンある場合）
export X_BEARER_TOKEN='あなたのトークン'
python export_x_posts.py --username shinkaron --outdir ./x_archive --chunk-mb 20

# 4-B) トークン不要版を実行
python export_x_posts_snscrape.py --username shinkaron --outdir ./x_archive --chunk-mb 20
```

## Windows (PowerShell) 例

```powershell
cd $HOME\Desktop
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests snscrape

# API版
$env:X_BEARER_TOKEN="あなたのトークン"
python .\export_x_posts.py --username shinkaron --outdir .\x_archive --chunk-mb 20

# 非API版
python .\export_x_posts_snscrape.py --username shinkaron --outdir .\x_archive --chunk-mb 20
```

## よくある失敗

- `ModuleNotFoundError` が出る
  - `pip install ...` をしていないか、仮想環境を有効化していない。
- `X_BEARER_TOKEN is not set`
  - API版を使っていてトークン環境変数が未設定。
- `snscrape` で取得できない
  - X側仕様変更による一時的不具合の可能性。時間を置くかAPI版を使用。

## 出力ファイル

- `x_archive/` に `*_0001.txt`, `*_0002.txt`... と20MBごとに分割保存されます。
