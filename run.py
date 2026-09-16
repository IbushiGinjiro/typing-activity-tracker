"""PyInstallerのビルド用エントリポイント。

`app/main.py`を直接ビルド対象にすると、PyInstallerがそれをトップレベルスクリプト扱いして
`app`パッケージの相対importが壊れる(`ImportError: attempted relative import with no known
parent package`)ため、`app`を絶対importするこのファイルを経由させる。
"""
from app.main import main

if __name__ == "__main__":
    main()
