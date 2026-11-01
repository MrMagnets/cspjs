"""CSP 初赛训练系统 —— 后端应用包。

注意：Cloudflare Workers 的 entrypoint 不是以 package 形式加载的，应用内部统一使用
顶层绝对导入（``from config import settings``）。为了让本地 ``uvicorn app.main:app``、
``python -m app.seed``、``python -m app.passwd`` 也能解析这些顶层模块，
这里把 ``app/`` 放进 ``sys.path``。main.py 里还有一份同样的保护，供 Workers 直接
加载 ``app/main.py`` 时使用。
"""
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

__version__ = "1.0.0"
