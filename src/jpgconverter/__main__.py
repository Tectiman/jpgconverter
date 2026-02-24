#!/usr/bin/env python3
"""
JPEG 批量转换器 - 配置文件版本
支持双向转换：JPG ↔ HEIC/AVIF/JXL
用法：uv run python -m jpgconverter -c config.json
"""

import argparse
import json
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import local

# 线程本地存储
_thread_data = local()
_shutdown = False


def signal_handler(signum, frame):
    global _shutdown
    _shutdown = True
    print("\n⚠️  收到中断信号，正在停止...", flush=True)


def init_worker():
    """每个线程初始化一次 - 注册所有格式"""
    from pillow_heif import register_heif_opener, from_pillow, options
    try:
        from pillow_avif import AvifImagePlugin  # noqa: F401
    except ImportError:
        pass
    try:
        from pillow_jxl import JpegXLImagePlugin  # noqa: F401
    except ImportError:
        pass

    options.DECODE_THREADS = 4
    register_heif_opener()

    _thread_data.from_pillow = from_pillow
    _thread_data.initialized = True


def get_worker():
    if not getattr(_thread_data, 'initialized', False):
        init_worker()
    return _thread_data


def convert_to_modern(inp, out, quality, fmt):
    """JPG 转 HEIC/AVIF/JXL"""
    try:
        from PIL import Image
        worker = get_worker()

        with Image.open(inp) as img:
            exif = img.info.get("exif")
            if img.mode != "RGB":
                img = img.convert("RGB")
            if fmt == "heic":
                heif = worker.from_pillow(img)
                heif.save(out, quality=quality, exif=exif)
            elif fmt == "avif":
                img.save(out, format="AVIF", quality=quality, exif=exif)
            elif fmt == "jxl":
                img.save(out, format="JXL", quality=quality, exif=exif)
            else:
                return False, f"未知格式：{fmt}"
        return True, ""
    except Exception as e:
        return False, str(e)


def convert_to_jpg(inp, out, quality, fmt):
    """HEIC/AVIF/JXL 转 JPG"""
    try:
        from PIL import Image
        # 确保所有插件已注册
        get_worker()

        with Image.open(inp) as img:
            exif = img.info.get("exif")
            # 保持原始模式，如果需要再转换
            if img.mode in ("RGBA", "LA", "P"):
                # 带透明通道的图片，转换为白色背景
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # 保存为 JPEG，保留 EXIF
            img.save(out, format="JPEG", quality=quality, exif=exif)
        return True, ""
    except Exception as e:
        return False, str(e)


def find_files(directory, input_format):
    """根据输入格式查找文件"""
    if not directory.exists():
        return []

    ext_map = {
        "jpg": {".jpg", ".jpeg", ".JPG", ".JPEG"},
        "heic": {".heic", ".HEIC", ".heif", ".HEIF"},
        "avif": {".avif", ".AVIF"},
        "jxl": {".jxl", ".JXL"},
    }

    exts = ext_map.get(input_format, set())
    return sorted(f for f in directory.iterdir() if f.is_file() and f.suffix in exts)


def get_output_ext(input_format, output_format):
    """获取输出文件扩展名"""
    ext_map = {
        "jpg": ".jpg",
        "heic": ".heic",
        "avif": ".avif",
        "jxl": ".jxl",
    }

    if output_format:
        return ext_map.get(output_format, f".{output_format}")

    # 反向转换时输出 jpg
    if input_format in ("heic", "avif", "jxl"):
        return ".jpg"

    return ext_map.get(input_format, ".out")


def process_task(task):
    """处理任务"""
    name = task.get("name", "未命名")
    inp = Path(task["input_path"])
    out = Path(task["output_path"]) if task.get("output_path") else None
    input_fmt = task.get("input_format", "").lower()
    output_fmt = task.get("output_format", "").lower()
    quality = task.get("quality", 90)
    skip = task.get("skip_existing", True)

    # 自动检测输入格式
    if not input_fmt:
        # 根据输出格式推断输入格式
        if output_fmt == "jpg":
            input_fmt = "auto"  # 自动检测所有现代格式
        else:
            input_fmt = "jpg"  # 默认从 JPG 转换

    # 确定输出格式
    if not output_fmt:
        if input_fmt == "jpg":
            output_fmt = "heic"  # 默认转为 HEIC
        else:
            output_fmt = "jpg"  # 反向转换

    # 确定转换方向
    if input_fmt == "auto":
        # 自动模式：处理所有支持的格式，转为 JPG
        convert_func = lambda i, o, q, f: convert_to_jpg(i, o, q, f)
        display_name = "自动 (HEIC/AVIF/JXL → JPG)"
    elif input_fmt == "jpg":
        convert_func = lambda i, o, q, f: convert_to_modern(i, o, q, f)
        display_name = f"JPG → {output_fmt.upper()}"
    else:
        convert_func = lambda i, o, q, f: convert_to_jpg(i, o, q, f)
        display_name = f"{input_fmt.upper()} → JPG"

    if not inp.exists():
        print(f"❌ [{name}] 目录不存在：{inp}", flush=True)
        return 0, 0, 0

    if out is None:
        out = inp / f"converted_{output_fmt}"
    out.mkdir(parents=True, exist_ok=True)

    # 查找输入文件
    if input_fmt == "auto":
        all_files = []
        for fmt in ["heic", "avif", "jxl"]:
            all_files.extend(find_files(inp, fmt))
        files = sorted(set(all_files))
    else:
        files = find_files(inp, input_fmt)

    total = len(files)

    if total == 0:
        print(f"⚠️  [{name}] 未找到文件 (格式：{input_fmt})", flush=True)
        return 0, 0, 0

    out_ext = get_output_ext(input_fmt, output_fmt)

    print(f"\n{'='*60}", flush=True)
    print(f"📋 任务：{name}", flush=True)
    print(f"   输入：{inp}", flush=True)
    print(f"   输出：{out}", flush=True)
    print(f"   转换：{display_name}", flush=True)
    print(f"   质量：{quality}", flush=True)
    print(f"   文件：{total}", flush=True)
    print(f"{'-'*60}", flush=True)

    # 构建任务列表
    tasks = []
    skip_count = 0
    for f in files:
        o = out / f"{f.stem}{out_ext}"
        if skip and o.exists():
            skip_count += 1
            continue
        # 传递输出格式给转换函数
        tasks.append((f, o, output_fmt if input_fmt != "auto" else f.suffix.lstrip(".")))

    to_process = len(tasks)
    if to_process == 0:
        print("✅ 所有文件已存在", flush=True)
        return 0, 0, skip_count

    print(f"🔄 开始处理 ({to_process} 个文件)...", flush=True)
    start = time.time()
    last = start
    ok = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(convert_func, i, o, quality, f): (i, o) for i, o, f in tasks}
        for i, fut in enumerate(as_completed(futs), 1):
            if _shutdown:
                print(f"\n⚠️  中断，已处理 {i-1}/{to_process}", flush=True)
                break
            inp_f, _ = futs[fut]
            try:
                s, e = fut.result()
                if s:
                    ok += 1
                    print(f"[{i}/{to_process}] ✓ {inp_f.name}", flush=True)
                else:
                    fail += 1
                    print(f"[{i}/{to_process}] ✗ {inp_f.name} - {e}", flush=True)
            except Exception as e:
                fail += 1
                print(f"[{i}/{to_process}] ✗ {inp_f.name} - {e}", flush=True)

            now = time.time()
            if now - last >= 10 and i < to_process:
                el = now - start
                r = i / el
                eta = (to_process - i) / r
                print(f"⏳ {i}/{to_process} ({r:.1f} 文件/秒，剩余{eta:.0f}秒)", flush=True)
                last = now

    el = time.time() - start
    print(f"\n✅ 成功:{ok}, 失败:{fail}, 跳过:{skip_count} (耗时:{el:.0f}秒)", flush=True)
    return ok, fail, skip_count


def main():
    p = argparse.ArgumentParser(description="JPEG 批量转换器 (支持双向转换)")
    p.add_argument("-c", "--config", type=Path, required=True, help="配置文件")
    args = p.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not args.config.exists():
        print(f"❌ 配置不存在：{args.config}", flush=True)
        sys.exit(1)

    with open(args.config) as f:
        cfg = json.load(f)

    tasks = cfg.get("tasks", [])
    if not tasks:
        print("⚠️  无任务", flush=True)
        sys.exit(0)

    print("=" * 60, flush=True)
    print("🚀 JPEG 批量转换器", flush=True)
    print("=" * 60, flush=True)
    print(f"📁 配置：{args.config}", flush=True)
    print(f"📝 任务：{len(tasks)}", flush=True)

    ok = fail = skip = 0
    for t in tasks:
        if not t.get("enabled", True):
            print(f"⊗ 跳过：{t.get('name')}", flush=True)
            continue
        if _shutdown:
            print("⚠️  已停止", flush=True)
            break
        a, b, c = process_task(t)
        ok += a
        fail += b
        skip += c

    print("\n" + "=" * 60, flush=True)
    print(f"📊 总计：成功{ok}, 失败{fail}, 跳过{skip}", flush=True)
    print("=" * 60, flush=True)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
