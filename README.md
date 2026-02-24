# jpgconverter

简单高效的 JPEG 转 HEIC/AVIF/JXL 批量转换工具，支持**双向转换**和配置文件。

## 安装

### 前置要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)（推荐的包管理器）

### 安装 uv

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**使用 pip:**
```bash
pip install uv
```

### 安装项目依赖

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/jpgconverter.git
cd jpgconverter

# 同步依赖
uv sync
```

## 功能特性

- ✅ **双向转换**: 支持 JPG ↔ HEIC/AVIF/JXL
- ✅ **完整保留 EXIF** 信息（时间、地点、地点、设备）
- ✅ **多线程处理**，高效批量转换
- ✅ **配置文件**支持，可定义多个任务
- ✅ **跳过已存在**文件，支持断点续传
- ✅ **质量可调** (0-100，默认 90)
- ✅ **实时进度**显示和剩余时间估算

## 平台支持

| 平台 | 状态 | 说明 |
|------|------|------|
| **Linux** | ✓ 完全支持 | x86_64, ARM64 |
| **macOS** | ✓ 完全支持 | Intel, Apple Silicon |
| **Windows** | ✓ 支持 | x86_64, ARM64 |

> 注意：某些格式插件在特定平台上的性能可能有所不同，特别是 AVIF 和 JXL 编解码器依赖于底层系统库。

## 支持的格式

| 转换方向 | 格式 | 扩展名 | 说明 |
|------|------|--------|------|
| JPG → 现代格式 | HEIC | `.heic` | 苹果主导，iOS 原生支持 |
| JPG → 现代格式 | AVIF | `.avif` | AOM 联盟标准，网页友好 |
| JPG → 现代格式 | JXL | `.jxl` | 开源标准，编解码速度快 |
| 现代格式 → JPG | HEIC | `.heic`/`.heif` | 转回 JPG 保留 EXIF |
| 现代格式 → JPG | AVIF | `.avif` | 转回 JPG 保留 EXIF |
| 现代格式 → JPG | JXL | `.jxl` | 转回 JPG 保留 EXIF |

## 快速开始

### 1. 编辑配置文件

```json
{
  "tasks": [
    {
      "name": "我的照片",
      "input_path": "/path/to/photos",
      "output_path": "/path/to/output",
      "output_format": "heic",
      "quality": 90,
      "skip_existing": true,
      "enabled": true
    }
  ]
}
```

### 2. 运行转换

```bash
# 使用配置文件
uv run python -m jpgconverter -c config.json

# 或使用命令行脚本
uv run jpgconverter -c config.json
```

## 配置参数

### 任务配置

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `name` | string | 否 | 任务名称 | "未命名" |
| `input_path` | string | 是 | 输入目录 | - |
| `output_path` | string | 否 | 输出目录 | `<input>/converted_<format>` |
| `input_format` | string | 否 | 输入格式 (jpg/heic/avif/jxl/auto) | 自动检测 |
| `output_format` | string | 否 | 输出格式 (jpg/heic/avif/jxl) | 自动推断 |
| `quality` | int | 否 | 质量 (0-100) | 90 |
| `skip_existing` | bool | 否 | 跳过已存在文件 | true |
| `enabled` | bool | 否 | 是否启用任务 | true |

### 转换模式

| input_format | output_format | 转换方向 |
|--------------|---------------|----------|
| `jpg` | `heic`/`avif`/`jxl` | JPG → 现代格式 |
| `heic`/`avif`/`jxl` | `jpg` | 现代格式 → JPG |
| `auto` | `jpg` | 自动检测所有现代格式转 JPG |
| (空) | (空) | 默认：JPG → HEIC |

### 正向转换示例 (JPG → HEIC/AVIF/JXL)

```json
{
  "tasks": [
    {
      "name": "JPG 转 HEIC",
      "input_path": "/photos/vacation",
      "output_path": "/output/heic",
      "input_format": "jpg",
      "output_format": "heic",
      "quality": 95,
      "skip_existing": true
    },
    {
      "name": "JPG 转 AVIF",
      "input_path": "/photos/daily",
      "input_format": "jpg",
      "output_format": "avif",
      "quality": 85
    }
  ]
}
```

### 反向转换示例 (HEIC/AVIF/JXL → JPG)

```json
{
  "tasks": [
    {
      "name": "HEIC 转 JPG",
      "input_path": "/photos/heic",
      "output_path": "/output/jpg",
      "input_format": "heic",
      "output_format": "jpg",
      "quality": 95
    },
    {
      "name": "AVIF 转 JPG",
      "input_path": "/photos/avif",
      "input_format": "avif",
      "output_format": "jpg",
      "quality": 90
    },
    {
      "name": "JXL 转 JPG",
      "input_path": "/photos/jxl",
      "input_format": "jxl",
      "output_format": "jpg"
    }
  ]
}
```

### 自动模式 (混合格式转 JPG)

```json
{
  "tasks": [
    {
      "name": "混合格式转 JPG",
      "input_path": "/photos/mixed",
      "input_format": "auto",
      "output_format": "jpg",
      "quality": 95
    }
  ]
}
```

## 内存管理

### 问题说明

1. `signal.alarm()` 无法中断底层 C 库阻塞
2. `multiprocessing` 的 `fork` 模式可能导致死锁
3. 大量并发进程可能消耗大量内存

### 解决方案

**运行前清理内存：**
```bash
# 清理残留 Python 进程
pkill -9 python
sleep 1

# 运行转换
uv run python -m jpgconverter -c config.json
```

**推荐配置：**
- 线程数：4-8（不要超过 CPU 核心数）
- 批量处理：大文件分批转换
- 监控内存：`watch -n1 free -h`

## 依赖

```toml
[dependencies]
pillow = "*"
pillow-heif = "*"
pillow-avif-plugin = "*"
pillow-jxl-plugin = "*"
```

## 项目结构

```
jpgconverter/
├── config.json          # 配置文件
├── config.example.json  # 配置示例
├── pyproject.toml       # 项目配置
├── README.md            # 本文档
├── .gitignore           # Git 忽略文件
├── src/jpgconverter/    # 主程序包
│   ├── __init__.py
│   └── __main__.py      # 主入口
├── photos/              # 示例照片目录
└── test_pic/            # 测试图片目录
```

## Ctrl+C 中断

按 Ctrl+C 可安全中断转换，已处理的文件不会回滚。

## 许可证

MIT License

## 相关项目

- [pillow-heif](https://github.com/bigcat88/pillow-heif) - HEIF/HEIC 支持
- [pillow-avif-plugin](https://github.com/fdintino/pillow-avif-plugin) - AVIF 支持
- [pillow-jxl-plugin](https://github.com/Akanoa/pillow-jxl-plugin) - JPEG XL 支持
