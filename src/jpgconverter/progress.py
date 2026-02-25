"""进度显示和任务执行模块"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from . import converter
from .config_data import TaskConfig


@dataclass
class TaskResult:
    """任务执行结果"""

    success: int = 0
    failed: int = 0
    skipped: int = 0


class ProgressBar:
    """进度条显示"""

    def __init__(self, total: int, description: str = ""):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.lock = threading.Lock()

    def update(self, n: int = 1):
        """更新进度"""
        with self.lock:
            self.current += n
            self._display()

    def _display(self):
        """显示进度条"""
        if self.total == 0:
            return

        elapsed = time.time() - self.start_time
        percentage = self.current / self.total * 100
        
        # 计算 ETA
        if self.current > 0:
            eta = elapsed * (self.total - self.current) / self.current
        else:
            eta = 0

        # 进度条可视化
        bar_length = 30
        filled_length = int(bar_length * self.current // self.total)
        bar = '█' * filled_length + '·' * (bar_length - filled_length)

        # 原地刷新
        print(f'\r{self.description} |{bar}| {percentage:5.1f}% [{self.current}/{self.total}] '
              f'{elapsed:5.1f}s 剩{eta:5.1f}s', end='', flush=True)

        if self.current >= self.total:
            print()  # 完成后换行

    def close(self):
        """完成进度条"""
        with self.lock:
            self.current = self.total
            self._display()


class TaskProcessor:
    """任务处理器（多线程优化版）"""

    def __init__(
        self,
        max_workers: int = 8,
        batch_size: int = 50,
        show_progress: bool = True,
    ):
        """
        初始化任务处理器

        Args:
            max_workers: 最大工作线程数
            batch_size: 批处理大小
            show_progress: 是否显示进度条
        """
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.show_progress = show_progress

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

        # 准备转换任务（跳过已存在的文件）
        tasks = self._prepare_tasks(files, output_dir, input_fmt, output_fmt, task.skip_existing)
        to_process = len(tasks)
        skipped_count = total - to_process

        if to_process == 0:
            print("✅ 所有文件已存在", flush=True)
            return TaskResult(skipped=skipped_count)

        # 执行转换（批处理 + 多线程）
        result = self._execute_tasks_batch(tasks, task.quality, output_fmt)
        result.skipped = skipped_count
        return result

    def _find_files(self, directory: Path, input_format: str) -> List[Path]:
        """查找输入文件"""
        if input_format == "auto":
            all_files = []
            for fmt in ["heic", "avif", "jxl"]:
                all_files.extend(converter.find_files(directory, fmt))
            return sorted(set(all_files))
        return converter.find_files(directory, input_format)

    def _prepare_tasks(
        self,
        files: List[Path],
        output_dir: Path,
        input_format: str,
        output_format: str,
        skip_existing: bool,
    ) -> List[Tuple[Path, Path, str]]:
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

    def _execute_tasks_batch(
        self,
        tasks: List[Tuple[Path, Path, str]],
        quality: int,
        output_format: str,
    ) -> TaskResult:
        """
        批处理 + 多线程执行转换

        Args:
            tasks: [(输入文件，输出文件，输出格式), ...]
            quality: 质量
            output_format: 输出格式

        Returns:
            执行结果
        """
        to_process = len(tasks)
        result = TaskResult()

        # 分组批处理
        batches = [
            tasks[i:i + self.batch_size]
            for i in range(0, len(tasks), self.batch_size)
        ]

        print(f"🔄 开始处理 ({to_process} 个文件，{len(batches)} 批，{self.max_workers} 线程)...", flush=True)

        # 进度条
        if self.show_progress:
            progress = ProgressBar(to_process, "处理进度")
        else:
            progress = None

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交每个批次
            futures = {
                executor.submit(self._process_batch, batch, quality): batch
                for batch in batches
            }

            # 处理完成的批次
            for future in as_completed(futures):
                batch = futures[future]
                try:
                    batch_result = future.result()
                    result.success += batch_result['success']
                    result.failed += batch_result['failed']

                    # 更新进度条
                    if progress:
                        progress.update(len(batch))

                except Exception as e:
                    # 批次整体失败
                    result.failed += len(batch)
                    print(f"\n❌ 批次处理失败：{e}", flush=True)

        # 关闭进度条
        if progress:
            progress.close()

        # 打印最终结果
        elapsed = time.time() - start_time
        print(
            f"\n✅ 成功:{result.success}, 失败:{result.failed}, 跳过:{result.skipped} "
            f"(耗时:{elapsed:.0f}秒，速度:{to_process/elapsed:.1f}文件/秒)",
            flush=True,
        )

        return result

    def _process_batch(
        self,
        batch: List[Tuple[Path, Path, str]],
        quality: int,
    ) -> dict:
        """
        处理单个批次的文件

        Args:
            batch: [(输入文件，输出文件，输出格式), ...]
            quality: 质量

        Returns:
            {'success': int, 'failed': int}
        """
        batch_result = {'success': 0, 'failed': 0}

        for inp, out, fmt in batch:
            try:
                success, error = self._convert_file(inp, out, quality, fmt)
                if success:
                    batch_result['success'] += 1
                else:
                    batch_result['failed'] += 1
                    print(f"\n✗ {inp.name} - {error}", flush=True)
            except Exception as e:
                batch_result['failed'] += 1
                print(f"\n✗ {inp.name} - {e}", flush=True)

        return batch_result

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
