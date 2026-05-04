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


## Windowsで `source` エラーが出る場合

そのエラーは **PowerShell ではなく cmd.exe** で、Linux/macOS用コマンド（`source .venv/bin/activate`）を実行したときに出ます。

### cmd.exe の正しい手順

```bat
cd %USERPROFILE%\OneDrive\Desktop
py -m venv .venv
.venv\Scripts\activate.bat
pip install requests snscrape
python export_x_posts_snscrape.py --username shinkaron --outdir .\x_archive --chunk-mb 20
```

### PowerShell の正しい手順

```powershell
cd $HOME\OneDrive\Desktop
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests snscrape
python .\export_x_posts_snscrape.py --username shinkaron --outdir .\x_archive --chunk-mb 20
```

> 実行ポリシーで `Activate.ps1` が止められたら、PowerShellを管理者で開いて
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` を一度実行してください。



## 「scrapling で回避できないの？」への回答

短く言うと、**安定的な回避はできません**。  
`scrapling` はHTML取得や解析を助けるライブラリですが、XのGraphQL/APIブロックや認証要件そのものを恒久的に突破するものではありません。

- 非公式スクレイピング（`snscrape` / ブラウザ自動化 / HTML解析）は、X側仕様変更で止まりやすい
- 404/429/ログイン壁はスクレイパー側だけで完全回避し続けるのが難しい
- 長期運用の安定性を優先するなら公式API利用が現実的

そのため本ツールは、
1) まず `snscrape` を試す
2) 失敗が続く場合は公式API版へ切り替える

という運用を推奨します。

## APIなしで「見えている画面」から取る方法（ブラウザ自動化）

「Xで普通に見えているなら取りたい」という場合は、`export_x_posts_browser.py` を使えます。
これは**実ブラウザを開いて手動ログイン後、見えているタイムラインをスクロール収集**する方式です。

```bash
pip install playwright
playwright install chromium
python export_x_posts_browser.py --username shinkaron --outdir ./x_archive --chunk-mb 20 --max-posts 500
```

- ログイン壁が出たらブラウザで手動ログイン
- タイムラインが見えたらターミナルで Enter
- その後スクロールしながら抽出

注意:
- UI変更で壊れる可能性はあります
- 取得できるのは「表示できた範囲」が中心です
- 長期安定は公式APIのほうが高いです

## 既に開いているEdgeセッションを使いたい場合（手動ログイン省略寄り）

可能です。`export_x_posts_browser_attach.py` は、**起動済みEdgeにCDP接続**して取得します。

### 1) Edgeをリモートデバッグ付きで起動（Windows例）

```bat
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\edge-cdp"
```

> そのEdgeで `https://x.com/shinkaron` を開いて、必要なら一度ログインしてください。

### 2) 取得実行

```bash
pip install playwright
python export_x_posts_browser_attach.py --username shinkaron --outdir ./x_archive --chunk-mb 20 --max-posts 500 --cdp http://127.0.0.1:9222
```

補足:
- 既存タブに `https://x.com/shinkaron` があればそのタブを利用
- 完全ノーログイン保証ではない（セッション切れ時は再ログインが必要）


- 既定では、既存タブがなければ終了（= 既に開いているページ限定）
- 新規タブを許可したい場合のみ `--allow-open-new-page` を付ける
