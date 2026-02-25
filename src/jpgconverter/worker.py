"""插件初始化模块"""


def init_plugins() -> None:
    """
    全局注册一次图像格式插件

    在主程序启动时调用，确保所有格式插件已注册。
    """
    from pillow_heif import register_heif_opener, options

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
