"""工作线程初始化和信号处理"""

import signal
from threading import local

_thread_data = local()
_shutdown = False


def init_worker() -> None:
    """
    每个线程初始化一次 - 注册所有格式插件

    在线程池中使用时，每个工作线程需要调用此函数来注册图像格式插件。
    """
    from pillow_heif import register_heif_opener, from_pillow, options

    try:
        from pillow_avif import AvifImagePlugin  # noqa: F401
    except ImportError:
        pass

    try:
        from pillow_jxl import JpegXLImagePlugin  # noqa: F401
    except ImportError:
        pass

    # 设置 HEIF 解码线程数
    options.DECODE_THREADS = 4
    register_heif_opener()

    # 存储到线程本地变量
    _thread_data.from_pillow = from_pillow
    _thread_data.initialized = True


def get_worker():
    """
    获取当前线程的工作器

    如果当前线程尚未初始化，会自动调用 init_worker()。

    Returns:
        包含 from_pillow 等工具的线程本地对象
    """
    if not getattr(_thread_data, "initialized", False):
        init_worker()
    return _thread_data


def is_shutdown() -> bool:
    """检查是否已收到关闭信号"""
    return _shutdown


def setup_signal_handlers() -> None:
    """设置信号处理器"""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def _signal_handler(signum, frame) -> None:
    """信号处理函数"""
    global _shutdown
    _shutdown = True
    print("\n⚠️  收到中断信号，正在停止...", flush=True)
