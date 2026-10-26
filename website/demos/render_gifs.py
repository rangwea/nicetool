"""Encode real captures and explicitly labeled AI workflow illustrations as GIFs.

Requires Pillow only when rebuilding assets, not to run the site or platform.
"""

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
SIZE = (1120, 760)


def font(size: int, mono: bool = False):
    candidates = [
        os.environ.get("DEMO_FONT", ""),
        "/System/Library/Fonts/Menlo.ttc"
        if mono
        else "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        if mono
        else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError("Set DEMO_FONT to a font supporting Chinese and English")


def browser_frame(source, language, desktop=False):
    image = Image.new("RGB", SIZE, "#f1f5f2")
    frame = ImageOps.contain(
        source.convert("RGB"), (1080, 650), Image.Resampling.LANCZOS
    )
    image.paste(frame, ((SIZE[0] - frame.width) // 2, 55))
    draw = ImageDraw.Draw(image)
    draw.text(
        (25, 18),
        (
            "Codex Desktop"
            if desktop
            else "NiceTool 工作台"
            if language == "zh"
            else "NiceTool Workspace"
        ),
        font=font(16),
        fill="#597363",
    )
    label = (
        "真实界面录制 · 合成数据"
        if language == "zh"
        else "Recorded interface · synthetic data"
    )
    draw.text((25, 720), label, font=font(14), fill="#7b8e80")
    return image


def illustration_sequence(source, language, stage):
    """Animate explanatory step markers; never imply recorded desktop actions."""
    labels = {
        "create": {
            "zh": ["描述需求", "使用 NiceTool Skill", "生成与预览"],
            "en": ["Describe the task", "Use NiceTool Skill", "Create and preview"],
        },
        "publish": {
            "zh": ["验证预览", "发布工具", "核对状态"],
            "en": ["Verify the preview", "Publish the tool", "Check its state"],
        },
    }[stage][language]
    frame = ImageOps.contain(
        source.convert("RGB"), (1080, 620), Image.Resampling.LANCZOS
    )
    sequence = []
    for active in range(3):
        image = Image.new("RGB", SIZE, "#f3f7f3")
        image.paste(frame, ((SIZE[0] - frame.width) // 2, 45))
        draw = ImageDraw.Draw(image)
        disclosure = (
            "AI 生成流程示意"
            if language == "zh"
            else "AI-generated workflow illustration"
        )
        draw.text((25, 14), disclosure, font=font(16), fill="#3a6348")
        for index, label in enumerate(labels):
            x = 25 + index * 365
            fill = "#dcebdc" if active == index else "#edf2ed"
            draw.rounded_rectangle((x, 692, x + 340, 742), radius=7, fill=fill)
            draw.text(
                (x + 15, 705),
                f"0{index + 1}  {label}",
                font=font(17),
                fill="#355941" if active == index else "#839286",
            )
        sequence.append((image, 1600 if active < 2 else 2400))
    return sequence


def encode(sequence, target, poster_index):
    frames = [image for image, _ in sequence]
    durations = [duration for _, duration in sequence]
    if len(frames) < 2:
        raise ValueError("A demo requires at least two captured states")
    montage = Image.new("RGB", (280, 190 * len(frames)), "white")
    for index, frame in enumerate(frames):
        montage.paste(frame.resize((280, 190)), (0, index * 190))
    palette = montage.quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    indexed = [
        frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames
    ]
    indexed[0].save(
        target.with_suffix(".gif"),
        save_all=True,
        append_images=indexed[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    frames[poster_index].save(target.with_suffix(".webp"), quality=90, method=6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frames",
        type=Path,
        help="Recorded PNGs grouped as preview-zh, preview-en, use-zh, use-en with manifest.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT.parent / "assets/demos")
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=("create", "preview", "publish", "use"),
        default=["preview", "use"],
        help="Stages to encode; generated illustrations must be explicitly supplied and are labeled",
    )
    parser.add_argument(
        "--illustrations",
        type=Path,
        help="Explicitly AI-generated source PNGs for create/publish; these are never labeled as recordings",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for language in ("zh", "en"):
        sequences = {}
        for scenario in args.stages:
            if args.illustrations and scenario in {"create", "publish"}:
                source = Image.open(args.illustrations / f"{scenario}.png")
                sequences[scenario] = illustration_sequence(source, language, scenario)
                continue
            if args.frames is None:
                parser.error("--frames is required for actual recordings")
            directory = args.frames / f"{scenario}-{language}"
            manifest = json.loads((directory / "manifest.json").read_text())
            sequences[scenario] = [
                (
                    browser_frame(
                        Image.open(directory / frame["file"]),
                        language,
                        desktop=scenario in {"create", "publish"},
                    ),
                    frame["duration"],
                )
                for frame in manifest
            ]
        for name, sequence in sequences.items():
            target = args.output / f"{name}-{language}"
            encode(
                sequence,
                target,
                0
                if name == "use"
                else len(sequence) - 1
                if name in {"create", "publish"}
                else 0,
            )
            print(f"built {target.name}: {len(sequence)} frames")


if __name__ == "__main__":
    main()
