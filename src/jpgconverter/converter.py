"""核心转换功能模块"""

from pathlib import Path

from PIL import Image


def convert_to_modern(inp: Path, out: Path, quality: int, fmt: str) -> tuple[bool, str]:
    """
    JPG 转 HEIC/AVIF/JXL

    Args:
        inp: 输入文件路径
        out: 输出文件路径
        quality: 质量 (0-100)
        fmt: 输出格式 (heic/avif/jxl)

    Returns:
        (成功标志，错误信息)
    """
    try:
        # 使用 with 确保资源释放
        with Image.open(inp) as img:
            exif = img.info.get("exif")
            
            # 转换为 RGB
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # 复制一份避免引用问题
            rgb_img = img.copy()

        # 在 with 块外保存，避免文件句柄冲突
        with rgb_img:
            if fmt == "heic":
                from pillow_heif import from_pillow
                heif = from_pillow(rgb_img)
                heif.save(out, quality=quality, exif=exif)
            elif fmt == "avif":
                rgb_img.save(out, format="AVIF", quality=quality, exif=exif)
            elif fmt == "jxl":
                rgb_img.save(out, format="JXL", quality=quality, exif=exif)
            else:
                return False, f"未知格式：{fmt}"

        return True, ""
    except Exception as e:
        return False, str(e)


def convert_to_jpg(inp: Path, out: Path, quality: int, fmt: str) -> tuple[bool, str]:
    """
    HEIC/AVIF/JXL 转 JPG

    Args:
        inp: 输入文件路径
        out: 输出文件路径
        quality: 质量 (0-100)
        fmt: 输入格式 (heic/avif/jxl)

    Returns:
        (成功标志，错误信息)
    """
    try:
        # 使用 with 确保资源释放
        with Image.open(inp) as img:
            exif = img.info.get("exif")
            
            # 处理不同模式
            if img.mode in ("RGBA", "LA", "P"):
                # 带透明通道的图片，转换为白色背景
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                rgb_img = background
            elif img.mode != "RGB":
                rgb_img = img.convert("RGB")
            else:
                rgb_img = img.copy()

        # 在 with 块外保存
        with rgb_img:
            rgb_img.save(out, format="JPEG", quality=quality, exif=exif)

        return True, ""
    except Exception as e:
        return False, str(e)


def find_files(directory: Path, input_format: str) -> list[Path]:
    """
    根据输入格式查找文件

    Args:
        directory: 搜索目录
        input_format: 输入格式 (jpg/heic/avif/jxl)

    Returns:
        文件路径列表
    """
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


def get_output_ext(input_format: str, output_format: str | None) -> str:
    """
    获取输出文件扩展名

    Args:
        input_format: 输入格式
        output_format: 输出格式

    Returns:
        输出扩展名（包含点）
    """
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
