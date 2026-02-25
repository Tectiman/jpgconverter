"""进度显示和任务执行模块"""

import time
from dataclasses import dataclass
from pathlib import Path

from . import converter
from .config import TaskConfig


@dataclass
class TaskResult:
    """任务执行结果"""

    success: int = 0
    failed: int = 0
    skipped: int = 0


class TaskProcessor:
    """任务处理器（单线程模式）"""

    def __init__(self, status_interval: int = 10):
        """
        初始化任务处理器

        Args:
            status_interval: 状态更新间隔（秒）
        """
        self.status_interval = status_interval

    def process(self, task: TaskConfig) -> TaskResult:
        """
        处理单个任务

        Args:
            task: 任务配置

        Returns:
            任务执行结果
        """
        input_dir = Path(task.input_path)
        output_dir = task.resolve_output_path()
        input_fmt = task.resolve_input_format()
        output_fmt = task.resolve_output_format()

        # 验证输入目录
        if not input_dir.exists():
            print(f"❌ [{task.name}] 目录不存在：{input_dir}", flush=True)
            return TaskResult()

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        # 查找文件
        files = self._find_files(input_dir, input_fmt)
        total = len(files)

        if total == 0:
            print(f"⚠️  [{task.name}] 未找到文件 (格式：{input_fmt})", flush=True)
            return TaskResult()

        # 打印任务信息
        self._print_task_info(task, input_dir, output_dir, total)

        # 准备转换任务
        tasks = self._prepare_tasks(files, output_dir, input_fmt, output_fmt, task.skip_existing)
        to_process = len(tasks)

        if to_process == 0:
            print("✅ 所有文件已存在", flush=True)
            return TaskResult(skipped=total)

        # 执行转换
        return self._execute_tasks(tasks, task.quality, output_fmt)

    def _find_files(self, directory: Path, input_format: str) -> list[Path]:
        """查找输入文件"""
        if input_format == "auto":
            all_files = []
            for fmt in ["heic", "avif", "jxl"]:
                all_files.extend(converter.find_files(directory, fmt))
            return sorted(set(all_files))
        return converter.find_files(directory, input_format)

    def _prepare_tasks(
        self,
        files: list[Path],
        output_dir: Path,
        input_format: str,
        output_format: str,
        skip_existing: bool,
    ) -> list[tuple[Path, Path, str]]:
        """
        准备转换任务列表

        Returns:
            [(输入文件，输出文件，输出格式), ...]
        """
        tasks = []
        out_ext = converter.get_output_ext(input_format, output_format)

        for f in files:
            out_path = output_dir / f"{f.stem}{out_ext}"
            if skip_existing and out_path.exists():
                continue

            # 确定输出格式（auto 模式下从文件名推断）
            fmt = output_format if input_format != "auto" else f.suffix.lstrip(".")
            tasks.append((f, out_path, fmt))

        return tasks

    def _print_task_info(
        self, task: TaskConfig, input_dir: Path, output_dir: Path, total: int
    ) -> None:
        """打印任务信息"""
        separator = "=" * 60
        print(f"\n{separator}", flush=True)
        print(f"📋 任务：{task.name}", flush=True)
        print(f"   输入：{input_dir}", flush=True)
        print(f"   输出：{output_dir}", flush=True)
        print(f"   转换：{task.conversion_direction}", flush=True)
        print(f"   质量：{task.quality}", flush=True)
        print(f"   文件：{total}", flush=True)
        print(f"{separator}", flush=True)

    def _execute_tasks(
        self,
        tasks: list[tuple[Path, Path, str]],
        quality: int,
        output_format: str,
    ) -> TaskResult:
        """
        执行转换任务

        Args:
            tasks: [(输入文件，输出文件，输出格式), ...]
            quality: 质量
            output_format: 输出格式

        Returns:
            执行结果
        """
        to_process = len(tasks)
        print(f"🔄 开始处理 ({to_process} 个文件)...", flush=True)

        start_time = time.time()
        last_status_time = start_time
        result = TaskResult()

        # 单线程顺序执行
        for i, (inp_path, out_path, fmt) in enumerate(tasks, 1):
            try:
                success, error = self._convert_file(inp_path, out_path, quality, fmt)
                if success:
                    result.success += 1
                    print(f"[{i}/{to_process}] ✓ {inp_path.name}", flush=True)
                else:
                    result.failed += 1
                    print(f"[{i}/{to_process}] ✗ {inp_path.name} - {error}", flush=True)
            except KeyboardInterrupt:
                print(f"\n⚠️  中断，已处理 {i-1}/{to_process}", flush=True)
                break
            except Exception as e:
                result.failed += 1
                print(f"[{i}/{to_process}] ✗ {inp_path.name} - {e}", flush=True)

            # 定期输出进度
            now = time.time()
            if now - last_status_time >= self.status_interval and i < to_process:
                self._print_status(i, to_process, start_time)
                last_status_time = now

        # 打印最终结果
        elapsed = time.time() - start_time
        print(
            f"\n✅ 成功:{result.success}, 失败:{result.failed}, 跳过:{result.skipped} "
            f"(耗时:{elapsed:.0f}秒)",
            flush=True,
        )

        return result

    def _convert_file(
        self, inp: Path, out: Path, quality: int, fmt: str
    ) -> tuple[bool, str]:
        """
        转换单个文件

        Args:
            inp: 输入文件
            out: 输出文件
            quality: 质量
            fmt: 格式

        Returns:
            (成功标志，错误信息)
        """
        # 根据输出格式选择转换函数
        if fmt in ("heic", "avif", "jxl"):
            return converter.convert_to_modern(inp, out, quality, fmt)
        else:
            return converter.convert_to_jpg(inp, out, quality, fmt)

    def _print_status(self, current: int, total: int, start_time: float) -> None:
        """打印进度状态"""
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        remaining = (total - current) / rate if rate > 0 else 0
        print(f"⏳ {current}/{total} ({rate:.1f} 文件/秒，剩余{remaining:.0f}秒)", flush=True)
