"""
JPEG 批量转换器 - 支持 HEIC/AVIF/JXL 双向转换
"""

__version__ = "2.0.0"

# 全局注册一次插件
from .worker import init_plugins
init_plugins()

from .converter import convert_to_jpg, convert_to_modern, find_files, get_output_ext
from .progress import TaskProcessor, ProgressBar, TaskResult
from .config_data import TaskConfig, AppConfig

__all__ = [
    "__version__",
    "convert_to_jpg",
    "convert_to_modern",
    "find_files",
    "get_output_ext",
    "TaskProcessor",
    "ProgressBar",
    "TaskResult",
    "TaskConfig",
    "AppConfig",
]
