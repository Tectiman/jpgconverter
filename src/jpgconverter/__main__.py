#!/usr/bin/env python3
"""
JPEG 批量转换器 - 配置文件版本
支持双向转换：JPG ↔ HEIC/AVIF/JXL

用法:
    uv run python -m jpgconverter -c config.json
    uv run jpgconverter -c config.json
"""

import argparse
import sys
from pathlib import Path

from .config_data import AppConfig
from .progress import TaskProcessor, TaskResult


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="JPEG 批量转换器 (支持双向转换)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -c config.json    使用配置文件
  %(prog)s -c config.json -w 4 -b 100  指定线程数和批大小

支持的转换方向:
  JPG → HEIC/AVIF/JXL        压缩为现代格式
  HEIC/AVIF/JXL → JPG        转回兼容格式
  auto → JPG                 自动检测混合格式转 JPG
        """,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="配置文件路径 (JSON 格式)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=None,
        help="并发线程数 (默认：8)",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=None,
        help="批处理大小 (默认：50)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="不显示进度条",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> AppConfig:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        应用配置对象

    Raises:
        SystemExit: 配置文件不存在或格式错误
    """
    if not config_path.exists():
        print(f"❌ 配置文件不存在：{config_path}", flush=True)
        sys.exit(1)

    try:
        return AppConfig.from_file(config_path)
    except Exception as e:
        print(f"❌ 配置文件解析失败：{e}", flush=True)
        sys.exit(1)


def load_advanced_config():
    """
    加载高级配置（可选的 config.py）

    Returns:
        配置字典，如果不存在则返回默认值
    """
    try:
        # 尝试从当前目录和包目录加载
        import importlib.util
        import os

        # 优先加载当前目录的 config.py
        local_config = Path("config.py")
        if local_config.exists():
            spec = importlib.util.spec_from_file_location("config", local_config)
            cfg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg)
            print(f"✓ 加载本地配置文件：{local_config.absolute()}", flush=True)
            return cfg

        # 尝试加载包内的 config.py
        package_config = Path(__file__).parent / "config.py"
        if package_config.exists():
            spec = importlib.util.spec_from_file_location("config", package_config)
            cfg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg)
            print(f"✓ 加载包配置文件：{package_config}", flush=True)
            return cfg

    except Exception as e:
        print(f"⚠ 加载高级配置失败：{e}", flush=True)

    # 返回空字典，使用默认值
    return {}


def check_dependencies():
    """
    检查依赖是否正常

    Returns:
        bool: 依赖检查是否通过
    """
    missing = []

    # 检查核心依赖
    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        missing.append("pillow-heif")

    if missing:
        print(f"⚠ 缺少依赖：{', '.join(missing)}", flush=True)
        print("  安装命令：uv add pillow-heif pillow-avif-plugin pillow-jxl-plugin", flush=True)
        return False

    # 可选依赖警告
    optional_missing = []
    try:
        import pillow_avif_plugin  # noqa: F401
    except ImportError:
        optional_missing.append("pillow-avif-plugin")

    try:
        import pillow_jxl_plugin  # noqa: F401
    except ImportError:
        optional_missing.append("pillow-jxl-plugin")

    if optional_missing:
        print(f"ℹ  未安装可选依赖：{', '.join(optional_missing)}", flush=True)
        print(f"   某些格式 (AVIF/JXL) 可能无法使用", flush=True)

    return True


def print_header(config_path: Path, task_count: int, workers: int, batch_size: int) -> None:
    """打印程序头部信息"""
    separator = "=" * 60
    print(separator, flush=True)
    print("🚀 JPEG 批量转换器", flush=True)
    print(separator, flush=True)
    print(f"📁 配置：{config_path}", flush=True)
    print(f"📝 任务：{task_count}", flush=True)
    print(f"⚙️  线程：{workers}, 批大小：{batch_size}", flush=True)


def print_summary(total_result: TaskResult, elapsed: float) -> None:
    """打印执行摘要"""
    separator = "=" * 60
    print(f"\n{separator}", flush=True)
    print(
        f"📊 总计：成功{total_result.success}, 失败{total_result.failed}, 跳过{total_result.skipped}",
        flush=True,
    )
    print(separator, flush=True)


def main() -> None:
    """主入口函数"""
    args = parse_args()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 加载高级配置（可选）
    adv_config = load_advanced_config()

    # 获取配置值（命令行 > 高级配置 > 默认值）
    max_workers = args.workers or adv_config.get('PERFORMANCE_OPTIONS', {}).get('max_workers', 8)
    batch_size = args.batch_size or adv_config.get('PERFORMANCE_OPTIONS', {}).get('batch_size', 50)
    show_progress = not args.no_progress and adv_config.get('PERFORMANCE_OPTIONS', {}).get('show_progress_bar', True)

    # 加载配置
    config = load_config(args.config)
    tasks = config.get_enabled_tasks()

    if not tasks:
        print("⚠️  没有启用的任务", flush=True)
        sys.exit(0)

    # 打印头部信息
    print_header(args.config, len(tasks), max_workers, batch_size)

    # 创建处理器并执行任务
    processor = TaskProcessor(
        max_workers=max_workers,
        batch_size=batch_size,
        show_progress=show_progress,
    )
    total_result = TaskResult()

    import time
    start_time = time.time()

    for task in tasks:
        result = processor.process(task)
        total_result.success += result.success
        total_result.failed += result.failed
        total_result.skipped += result.skipped

    elapsed = time.time() - start_time

    # 打印摘要
    print_summary(total_result, elapsed)

    # 根据失败情况设置退出码
    sys.exit(0 if total_result.failed == 0 else 1)


if __name__ == "__main__":
    main()
