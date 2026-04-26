#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPA Image API - 完整封装
基于 OpenAI Image API (Generations + Edits)

支持端点:
  POST /v1/images/generations  - 生成图片
  POST /v1/images/edits        - 编辑图片（含 mask 局部编辑）

环境变量:
  CPA_API_BASE  - 默认 http://<CPA_HOST>:<CPA_PORT>
  CPA_API_KEY   - 默认 <YOUR_API_KEY>
  CPA_OUT_DIR   - 默认 /tmp/gptimage

使用示例:
  # 生成
  python3 cpa_image_api.py "A beautiful sunset" --size 1536x1024 --quality high

  # 编辑
  python3 cpa_image_api.py "Make it green" --edit --image source.png

  # 局部编辑（mask）
  python3 cpa_image_api.py "Add a hat" --edit --image source.png --mask mask.png
"""

import json
import base64
import os
import sys
import time
import subprocess
import tempfile
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# =============================================================================
# 配置
# =============================================================================
API_BASE = os.environ.get("CPA_API_BASE", "http://<CPA_HOST>:<CPA_PORT>")
API_KEY = os.environ.get("CPA_API_KEY", "<YOUR_API_KEY>")
DEFAULT_OUTDIR = os.environ.get("CPA_OUT_DIR", "/tmp/gptimage")
DEFAULT_TIMEOUT = 180


# =============================================================================
# 数据模型
# =============================================================================
@dataclass
class GeneratedImage:
    """生成的图片结果"""
    index: int
    prompt: str
    b64_json: str
    revised_prompt: Optional[str] = None
    saved_path: Optional[str] = None
    file_size: int = 0

    @property
    def image_bytes(self) -> bytes:
        return base64.b64decode(self.b64_json)

    def save(self, filepath: str) -> str:
        with open(filepath, 'wb') as f:
            f.write(self.image_bytes)
        self.saved_path = filepath
        self.file_size = os.path.getsize(filepath)
        return filepath


@dataclass
class ImageGenConfig:
    """图片生成配置"""
    model: str = "gpt-image-2"
    size: Optional[str] = None          # e.g. "1024x1024", "1536x1024", "2048x2048"
    quality: Optional[str] = None       # "low" | "medium" | "high"
    n: int = 1                          # 1-10
    format: Optional[str] = None        # "png" | "jpeg" | "webp"
    output_compression: Optional[int] = None  # 0-100，PNG 只支持 100
    background: Optional[str] = None    # "opaque" | "auto"
    moderation: Optional[str] = None    # "auto" | "low"
    response_format: str = "b64_json"   # "b64_json" | "url"
    user: Optional[str] = None
    timeout: int = DEFAULT_TIMEOUT
    outdir: str = DEFAULT_OUTDIR
    filename_prefix: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        """构建 JSON payload"""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": "",  # caller fills this
            "n": self.n,
            "response_format": self.response_format,
        }
        if self.size:
            payload["size"] = self.size
        if self.quality:
            payload["quality"] = self.quality
        if self.format:
            if self.format == "png" and self.output_compression is not None and self.output_compression != 100:
                raise ValueError("PNG 格式只支持 output_compression=100")
            payload["format"] = self.format
        if self.output_compression is not None:
            payload["output_compression"] = self.output_compression
        if self.background:
            payload["background"] = self.background
        if self.moderation:
            payload["moderation"] = self.moderation
        if self.user:
            payload["user"] = self.user
        return payload


@dataclass
class ImageEditConfig:
    """图片编辑配置"""
    model: str = "gpt-image-2"
    image_path: str = ""              # 原图路径（必填）
    mask_path: Optional[str] = None   # mask 路径（可选）
    size: Optional[str] = None
    quality: Optional[str] = None
    n: int = 1
    format: Optional[str] = None
    output_compression: Optional[int] = None
    background: Optional[str] = None
    response_format: str = "b64_json"
    user: Optional[str] = None
    timeout: int = DEFAULT_TIMEOUT
    outdir: str = DEFAULT_OUTDIR
    filename_prefix: Optional[str] = None


# =============================================================================
# 核心请求函数
# =============================================================================
def _curl_json(endpoint: str, payload: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """发送 JSON POST 请求"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        data_file = f.name
    try:
        cmd = [
            'curl', '-s', '--max-time', str(timeout),
            '-H', f'Authorization: Bearer {API_KEY}',
            '-H', 'Content-Type: application/json',
            '-d', f'@{data_file}',
            f'{API_BASE}{endpoint}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        if result.returncode != 0:
            return {"_error": f"curl failed: {result.stderr}"}
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"_error": f"JSON decode failed: {e}", "_raw": result.stdout[:300]}
    except Exception as e:
        return {"_error": str(e)}
    finally:
        os.unlink(data_file)


def _curl_multipart(
    endpoint: str,
    prompt: str,
    image_path: str,
    mask_path: Optional[str] = None,
    model: str = "gpt-image-2",
    size: Optional[str] = None,
    quality: Optional[str] = None,
    n: int = 1,
    fmt: Optional[str] = None,
    output_compression: Optional[int] = None,
    background: Optional[str] = None,
    response_format: str = "b64_json",
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """发送 multipart/form-data POST 请求（用于 edits）"""
    if not os.path.exists(image_path):
        return {"_error": f"Image file not found: {image_path}"}
    if mask_path and not os.path.exists(mask_path):
        return {"_error": f"Mask file not found: {mask_path}"}

    cmd = [
        'curl', '-s', '--max-time', str(timeout),
        '-H', f'Authorization: Bearer {API_KEY}',
        '-F', f'model={model}',
        '-F', f'prompt={prompt}',
        '-F', f'image=@{image_path}',
        '-F', f'n={n}',
        '-F', f'response_format={response_format}',
    ]
    if mask_path:
        cmd.extend(['-F', f'mask=@{mask_path}'])
    if size:
        cmd.extend(['-F', f'size={size}'])
    if quality:
        cmd.extend(['-F', f'quality={quality}'])
    if fmt:
        cmd.extend(['-F', f'format={fmt}'])
    if output_compression is not None:
        cmd.extend(['-F', f'output_compression={output_compression}'])
    if background:
        cmd.extend(['-F', f'background={background}'])

    cmd.append(f'{API_BASE}{endpoint}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        if result.returncode != 0:
            return {"_error": f"curl failed: {result.stderr}"}
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"_error": f"JSON decode failed: {e}", "_raw": result.stdout[:300]}
    except Exception as e:
        return {"_error": str(e)}


def _parse_error(resp: Dict[str, Any]) -> Optional[str]:
    if "_error" in resp:
        return resp["_error"]
    err = resp.get("error")
    if err is not None:
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return msg[:200]
    return None

def _save_images(resp: Dict[str, Any], prompt: str, outdir: str, prefix: Optional[str] = None, expected_n: int = 1) -> List[GeneratedImage]:
    """
从响应中提取并保存图片
    检测实际返回的图片格式，确保使用正确的扩展名"""
    results = []
    timestamp = time.strftime("%m%d_%H%M%S")
    safe_prompt = "".join(c if c.isalnum() or c in "_-" or '\u4e00' <= c <= '\u9fff' else "_" for c in prompt[:30])
    base_name = prefix or f"{timestamp}_{safe_prompt}"

    data = resp.get("data", [])
    actual_count = len(data)
    if expected_n > 1 and actual_count != expected_n:
        print(f"    [⚠️] 请求 n={expected_n}，实际返回 {actual_count} 张（参数被上游限制）")

    for i, item in enumerate(data):
        b64 = item.get("b64_json", "")
        if not b64:
            continue

        # 检测实际图片格式
        img_bytes = base64.b64decode(b64)
        ext = _detect_format(img_bytes)

        img = GeneratedImage(
            index=i,
            prompt=prompt,
            b64_json=b64,
            revised_prompt=item.get("revised_prompt"),
        )

        filepath = os.path.join(outdir, f"{base_name}_{i}.{ext}")
        img.save(filepath)
        results.append(img)

    return results


def _detect_format(img_bytes: bytes) -> str:
    """通过文件头魔数检测图片格式"""
    if img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "png"
    if img_bytes[:2] == b'\xff\xd8':
        return "jpeg"
    if img_bytes[:4] == b'RIFF' and len(img_bytes) > 12 and img_bytes[8:12] == b'WEBP':
        return "webp"
    return "png"  # 默认


# =============================================================================
# 主要 API 函数
# =============================================================================
def generate(
    prompt: str,
    config: Optional[ImageGenConfig] = None,
) -> List[GeneratedImage]:
    """
    生成图片

    Args:
        prompt: 图片描述（原样传递，不会被修改或翻译）
        config: 生成配置

    Returns:
        GeneratedImage 列表

    Raises:
        RuntimeError: 生成失败时
    """
    if config is None:
        config = ImageGenConfig()

    os.makedirs(config.outdir, exist_ok=True)

    payload = config.to_payload()
    payload["prompt"] = prompt

    print(f"[生成] {prompt[:50]}...")
    print(f"    参数: size={config.size or 'default'} quality={config.quality or 'default'} n={config.n}")

    start = time.time()
    resp = _curl_json("/v1/images/generations", payload, timeout=config.timeout)
    elapsed = time.time() - start

    err = _parse_error(resp)
    if err:
        raise RuntimeError(f"生成失败: {err}")

    images = _save_images(resp, prompt, config.outdir, config.filename_prefix, expected_n=config.n)
    if not images:
        raise RuntimeError("响应中没有图片数据")

    total_kb = sum(img.file_size for img in images) // 1024
    print(f"[✅] 成功生成 {len(images)} 张图片，共 {total_kb}KB，耗时 {elapsed:.1f}s")
    for img in images:
        print(f"    → {img.saved_path} ({img.file_size // 1024}KB)")
        if img.revised_prompt:
            print(f"      修订: {img.revised_prompt[:60]}...")

    return images


def edit(
    prompt: str,
    image_path: str,
    mask_path: Optional[str] = None,
    config: Optional[ImageEditConfig] = None,
) -> List[GeneratedImage]:
    """
    编辑图片

    Args:
        prompt: 编辑描述
        image_path: 原图路径（必填）
        mask_path: mask 图路径（可选，需含 alpha 通道的 PNG）
        config: 编辑配置

    Returns:
        GeneratedImage 列表
    """
    if config is None:
        config = ImageEditConfig()

    os.makedirs(config.outdir, exist_ok=True)

    print(f"[编辑] {prompt[:50]}...")
    print(f"    原图: {image_path}")
    if mask_path:
        print(f"    mask: {mask_path}")
    print(f"    参数: size={config.size or 'default'} quality={config.quality or 'default'}")

    start = time.time()
    resp = _curl_multipart(
        "/v1/images/edits",
        prompt=prompt,
        image_path=image_path,
        mask_path=mask_path,
        model=config.model,
        size=config.size,
        quality=config.quality,
        n=config.n,
        fmt=config.format,
        output_compression=config.output_compression,
        background=config.background,
        response_format=config.response_format,
        timeout=config.timeout,
    )
    elapsed = time.time() - start

    err = _parse_error(resp)
    if err:
        raise RuntimeError(f"编辑失败: {err}")

    images = _save_images(resp, prompt, config.outdir, config.filename_prefix, expected_n=config.n)
    if not images:
        raise RuntimeError("响应中没有图片数据")

    total_kb = sum(img.file_size for img in images) // 1024
    print(f"[✅] 成功编辑 {len(images)} 张图片，共 {total_kb}KB，耗时 {elapsed:.1f}s")
    for img in images:
        print(f"    → {img.saved_path} ({img.file_size // 1024}KB)")
        if img.revised_prompt:
            print(f"      修订: {img.revised_prompt[:60]}...")

    return images


# =============================================================================
# 快捷函数
# =============================================================================
def quick_generate(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "low",
    n: int = 1,
    outdir: str = DEFAULT_OUTDIR,
) -> List[GeneratedImage]:
    """快速生成"""
    config = ImageGenConfig(size=size, quality=quality, n=n, outdir=outdir)
    return generate(prompt, config)


def quick_edit(
    prompt: str,
    image_path: str,
    mask_path: Optional[str] = None,
    size: str = "1024x1024",
    outdir: str = DEFAULT_OUTDIR,
) -> List[GeneratedImage]:
    """快速编辑"""
    config = ImageEditConfig(image_path=image_path, mask_path=mask_path, size=size, outdir=outdir)
    return edit(prompt, image_path, mask_path, config)


# =============================================================================
# CLI 入口
# =============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="CPA Image API 图片生成与编辑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  生成图片:
    python3 cpa_image_api.py "A beautiful sunset" --size 1536x1024 --quality high

  编辑图片:
    python3 cpa_image_api.py "Make it green" --edit --image source.png

  局部编辑（mask）:
    python3 cpa_image_api.py "Add a red hat" --edit --image source.png --mask mask.png

  生成多张:
    python3 cpa_image_api.py "A flower" --n 4

  指定格式:
    python3 cpa_image_api.py "A cat" --format jpeg --compression 80
        """
    )
    parser.add_argument("prompt", help="图片描述 / 编辑描述")
    parser.add_argument("--edit", action="store_true", help="使用 edits 端点（编辑模式）")
    parser.add_argument("--image", help="原图路径（编辑模式必填）")
    parser.add_argument("--mask", help="mask 图路径（可选，需含 alpha 通道的 PNG）")
    parser.add_argument("--model", default="gpt-image-2", help="模型名称")
    parser.add_argument("--size", default="1024x1024", help="尺寸，默认 1024x1024")
    parser.add_argument("--quality", default="low", help="质量 (low/medium/high)")
    parser.add_argument("--n", type=int, default=1, help="生成数量 1-10")
    parser.add_argument("--format", dest="fmt", choices=["png", "jpeg", "webp"], help="输出格式")
    parser.add_argument("--compression", type=int, help="压缩率 0-100（PNG 只支持 100）")
    parser.add_argument("--background", choices=["opaque", "auto"], help="背景")
    parser.add_argument("--moderation", choices=["auto", "low"], help="审核级别")
    parser.add_argument("--outdir", "-o", default=DEFAULT_OUTDIR, help="输出目录")
    parser.add_argument("--prefix", help="文件名前缀")
    parser.add_argument("--timeout", type=int, default=180, help="超时秒数")

    args = parser.parse_args()

    # 验证参数
    if args.edit and not args.image:
        print("[❌] 编辑模式必须指定 --image")
        return 1

    if args.fmt == "png" and args.compression is not None and args.compression != 100:
        print("[❌] PNG 格式只支持 --compression 100")
        return 1

    try:
        if args.edit:
            config = ImageEditConfig(
                model=args.model,
                image_path=args.image,
                mask_path=args.mask,
                size=args.size,
                quality=args.quality,
                n=args.n,
                format=args.fmt,
                output_compression=args.compression,
                background=args.background,
                timeout=args.timeout,
                outdir=args.outdir,
                filename_prefix=args.prefix,
            )
            edit(args.prompt, args.image, args.mask, config)
        else:
            config = ImageGenConfig(
                model=args.model,
                size=args.size,
                quality=args.quality,
                n=args.n,
                format=args.fmt,
                output_compression=args.compression,
                background=args.background,
                moderation=args.moderation,
                timeout=args.timeout,
                outdir=args.outdir,
                filename_prefix=args.prefix,
            )
            generate(args.prompt, config)
    except RuntimeError as e:
        print(f"[❌] 失败: {e}")
        return 1
    except Exception as e:
        print(f"[❌] 异常: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
