from datetime import datetime
from pathlib import Path

from meme_generator import (
    MemeArgsModel,
    MemeArgsType,
    ParserArg,
    ParserOption,
    add_meme,
)
from meme_generator.exception import TextOverLength
from meme_generator.utils import make_jpg_or_gif
from pil_utils import BuildImage
from pydantic import Field

img_dir = Path(__file__).parent / "images"

help_text = "指定第一只猫（原图“up主”）的名字"


class Model(MemeArgsModel):
    name: str = Field("", description=help_text)


args_type = MemeArgsType(
    args_model=Model,
    args_examples=[Model(name="up主")],
    parser_options=[
        ParserOption(
            names=["-n", "--name", "名字"],
            args=[ParserArg(name="name", value="str")],
            help_text=help_text,
        ),
    ],
)

# 从左到右 5 张脸：(中心 x, 中心 y, 半径)
FACES = [
    (124, 496, 118),
    (336, 130, 134),
    (696, 110, 132),
    (924, 108, 130),
    (1124, 84, 128),
]


def rotated_text(
    text: str,
    size: tuple[int, int],
    angle: float,
    fill: tuple[int, int, int],
    max_fontsize: int,
    min_fontsize: int,
) -> BuildImage:
    canvas = BuildImage.new("RGBA", size)
    try:
        canvas.draw_text(
            (0, 0, size[0], size[1]),
            text,
            max_fontsize=max_fontsize,
            min_fontsize=min_fontsize,
            allow_wrap=True,
            lines_align="center",
            fill=fill,
        )
    except ValueError:
        raise TextOverLength(text)
    return canvas.rotate(angle, expand=True)


def paste_center(bg: BuildImage, img: BuildImage, center: tuple[int, int]):
    bg.paste(img, (center[0] - img.width // 2, center[1] - img.height // 2), alpha=True)


def urge_update(images: list[BuildImage], texts: list[str], args: Model):
    text = texts[0] if texts else "我干死你"
    name = args.name or (args.user_infos[0].name if args.user_infos else "") or "up主"

    frame = BuildImage.open(img_dir / "template.png").convert("RGBA")

    # 两个气泡里的文字
    paste_center(frame, rotated_text(text, (190, 50), 56, (0, 0, 0), 40, 16), (78, 96))
    frame.draw_text(
        (975, 255, 1215, 345),
        text,
        max_fontsize=40,
        min_fontsize=16,
        allow_wrap=True,
        lines_align="center",
        fill=(0, 0, 0),
    )
    # 第一只猫身上的名字
    paste_center(
        frame,
        rotated_text(name, (120, 40), 35, (90, 140, 190), 30, 12),
        (304, 404),
    )

    def make(imgs: list[BuildImage]) -> BuildImage:
        bg = frame.copy()
        # 从左到右依次替换脸，图片不足 5 张时剩下的保留原表情
        for img, (x, y, r) in zip(imgs, FACES):
            face = img.convert("RGBA").square().resize((r * 2, r * 2)).circle()
            bg.paste(face, (x - r, y - r), alpha=True)
        return bg

    return make_jpg_or_gif(images, make)


add_meme(
    "urge_update",
    urge_update,
    min_images=1,
    max_images=5,
    min_texts=0,
    max_texts=1,
    default_texts=["我干死你"],
    args_type=args_type,
    keywords=["快给我更新", "催更"],
    date_created=datetime(2026, 11, 1),
    date_modified=datetime(2026, 11, 1),
)
