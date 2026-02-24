"""配置处理模块"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


InputFormat = Literal["jpg", "heic", "avif", "jxl", "auto", ""]
OutputFormat = Literal["jpg", "heic", "avif", "jxl", ""]


@dataclass
class TaskConfig:
    """任务配置"""

    name: str = "未命名"
    input_path: str = ""
    output_path: str | None = None
    input_format: InputFormat = ""
    output_format: OutputFormat = ""
    quality: int = 90
    skip_existing: bool = True
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "TaskConfig":
        """从字典创建配置"""
        return cls(
            name=data.get("name", "未命名"),
            input_path=data.get("input_path", ""),
            output_path=data.get("output_path"),
            input_format=data.get("input_format", "").lower(),  # type: ignore
            output_format=data.get("output_format", "").lower(),  # type: ignore
            quality=data.get("quality", 90),
            skip_existing=data.get("skip_existing", True),
            enabled=data.get("enabled", True),
        )

    def resolve_output_path(self) -> Path:
        """解析输出路径，如果未指定则根据输入路径生成"""
        if self.output_path:
            return Path(self.output_path)

        input_dir = Path(self.input_path)
        output_fmt = self.output_format or "heic"
        return input_dir / f"converted_{output_fmt}"

    def resolve_input_format(self) -> InputFormat:
        """解析输入格式，根据输出格式推断"""
        if self.input_format:
            return self.input_format

        # 根据输出格式推断输入格式
        if self.output_format == "jpg":
            return "auto"  # 自动检测所有现代格式
        return "jpg"  # 默认从 JPG 转换

    def resolve_output_format(self) -> OutputFormat:
        """解析输出格式，根据输入格式推断"""
        if self.output_format:
            return self.output_format

        input_fmt = self.resolve_input_format()
        if input_fmt == "jpg":
            return "heic"  # 默认转为 HEIC
        return "jpg"  # 反向转换

    @property
    def conversion_direction(self) -> str:
        """获取转换方向描述"""
        input_fmt = self.resolve_input_format()
        output_fmt = self.resolve_output_format()

        if input_fmt == "auto":
            return "自动 (HEIC/AVIF/JXL → JPG)"
        elif input_fmt == "jpg":
            return f"JPG → {output_fmt.upper()}"
        else:
            return f"{input_fmt.upper()} → JPG"


@dataclass
class AppConfig:
    """应用配置"""

    tasks: list[TaskConfig] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "AppConfig":
        """从文件加载配置"""
        with open(path) as f:
            data = json.load(f)

        tasks_data = data.get("tasks", [])
        tasks = [TaskConfig.from_dict(t) for t in tasks_data]
        return cls(tasks=tasks)

    @classmethod
    def from_json(cls, json_str: str) -> "AppConfig":
        """从 JSON 字符串加载配置"""
        data = json.loads(json_str)
        tasks_data = data.get("tasks", [])
        tasks = [TaskConfig.from_dict(t) for t in tasks_data]
        return cls(tasks=tasks)

    def get_enabled_tasks(self) -> list[TaskConfig]:
        """获取所有启用的任务"""
        return [t for t in self.tasks if t.enabled]
