"""
JPEG 批量转换器 - 支持 HEIC/AVIF/JXL 双向转换

示例用法:
    from jpgconverter import convert_file, TaskConfig

    # 单个文件转换
    convert_file("input.jpg", "output.heic", quality=90)

    # 批量转换
    from jpgconverter.config import TaskConfig
    from jpgconverter.progress import TaskProcessor

    task = TaskConfig(
        name="我的照片",
        input_path="/path/to/photos",
        output_format="heic",
        quality=90
    )
    processor = TaskProcessor()
    result = processor.process(task)
"""

__version__ = "1.0.0"

from .converter import convert_to_jpg, convert_to_modern, find_files, get_output_ext
from .worker import get_worker, init_worker

__all__ = [
    "__version__",
    "convert_to_jpg",
    "convert_to_modern",
    "find_files",
    "get_output_ext",
    "get_worker",
    "init_worker",
]
