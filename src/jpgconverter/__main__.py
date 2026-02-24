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

from .config import AppConfig
from .progress import TaskProcessor, TaskResult
from .worker import setup_signal_handlers


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="JPEG 批量转换器 (支持双向转换)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -c config.json          使用配置文件
  %(prog)s -c config.json --jobs 4 指定线程数

支持的转换方向:
  JPG → HEIC/AVIF/JXL              压缩为现代格式
  HEIC/AVIF/JXL → JPG              转回兼容格式
  auto → JPG                       自动检测混合格式转 JPG
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
        "-j",
        "--jobs",
        type=int,
        default=8,
        help="并发线程数 (默认：8)",
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


def print_header(config_path: Path, task_count: int) -> None:
    """打印程序头部信息"""
    separator = "=" * 60
    print(separator, flush=True)
    print("🚀 JPEG 批量转换器", flush=True)
    print(separator, flush=True)
    print(f"📁 配置：{config_path}", flush=True)
    print(f"📝 任务：{task_count}", flush=True)


def print_summary(total_result: TaskResult) -> None:
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

    # 设置信号处理
    setup_signal_handlers()

    # 加载配置
    config = load_config(args.config)
    tasks = config.get_enabled_tasks()

    if not tasks:
        print("⚠️  没有启用的任务", flush=True)
        sys.exit(0)

    # 打印头部信息
    print_header(args.config, len(tasks))

    # 创建处理器并执行任务
    processor = TaskProcessor(max_workers=args.jobs)
    total_result = TaskResult()

    for task in tasks:
        result = processor.process(task)
        total_result.success += result.success
        total_result.failed += result.failed
        total_result.skipped += result.skipped

    # 打印摘要
    print_summary(total_result)

    # 根据失败情况设置退出码
    sys.exit(0 if total_result.failed == 0 else 1)


if __name__ == "__main__":
    main()
