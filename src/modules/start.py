"""
⚠️ 这里不是模块！这是一个陈旧副本，请直接删除本文件。

背景
────
本文件是项目根目录 `start.py`（Windows 启动器）的一份**过时副本**，
被误放进了 `modules/` 目录。

`module_loader.py` 会自动扫描本目录下所有 `.py` 文件并当成模块加载，
而本文件里只有一个 `Colors` 类（没有 `register_handlers` 方法），
于是每次启动都会产生一条失败记录：

    AttributeError: 'Colors' object has no attribute 'register_handlers'

这条错误被 module_loader 捕获后只写进日志，机器人照常启动，
所以外部表现是「启动成功了，但日志里有个看不懂的失败项」，
排查起来非常费劲。

正确的文件位置
──────────────
- 启动器（活的版本）：项目根目录 `start.py`
- 程序入口：`src/main.py`

本文件从未被任何代码 import（已全仓检索确认），
所以删除它不会有任何副作用；留着它只会每次启动多一条报错。

为什么保留一个会抛异常的文件
────────────────────────────
因为静默地留一个空文件，下次有人再误导入时依然不会有任何提示。
让它显式失败，比让它悄悄什么都不做更容易发现问题。
"""

raise ImportError(
    "modules/start.py 是一份陈旧副本，不是模块，不应被导入。"
    "请删除本文件；正确的启动方式是在项目根目录运行 `python start.py`，"
    "或直接运行 `python src/main.py`。"
)
