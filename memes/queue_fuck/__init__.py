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
from PIL import Image, ImageChops, ImageDraw
from pil_utils import BuildImage
from pydantic import Field

img_dir = Path(__file__).parent / "images"

help_text = "指定第一只猫的名字"


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

# 原图中挡在后面几张脸前面的猫身体（多边形），贴完脸后再盖回去
OCCLUDERS = [
    # 第 4 只猫的身体：挡住第 3 张脸的右侧和第 4 张脸的左下
    [
        (808, 0),
        (822, 0),
        (818, 40),
        (824, 80),
        (836, 90),
        (868, 150),
        (888, 210),
        (908, 300),
        (782, 300),
        (782, 140),
        (806, 120),
    ],
    # 第 5 只猫的身体：挡住第 4 张脸的右侧和第 5 张脸的左下
    [
        (1014, 40),
        (1032, 50),
        (1058, 80),
        (1068, 120),
        (1086, 165),
        (1104, 220),
        (1110, 300),
        (1010, 300),
        (1010, 240),
        (1018, 200),
        (1022, 150),
        (1030, 110),
        (1030, 50),
    ],
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


def queue_fuck(images: list[BuildImage], texts: list[str], args: Model):
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

    # 前景遮挡层：只保留 OCCLUDERS 区域的模板像素
    mask = Image.new("L", frame.size, 0)
    draw = ImageDraw.Draw(mask)
    for polygon in OCCLUDERS:
        draw.polygon(polygon, fill=255)
    # 多边形边缘混进的原表情像素（橙色、深棕色）不算身体，去掉
    r, _, b, _ = frame.image.split()
    not_emoji = ImageChops.subtract(r, b).point(lambda v: 0 if v > 50 else 255)
    front_img = frame.image.copy()
    front_img.putalpha(ImageChops.darker(mask, not_emoji))
    front = BuildImage(front_img)

    def make(imgs: list[BuildImage]) -> BuildImage:
        bg = frame.copy()
        # 从左到右依次替换脸，图片不足 5 张时剩下的保留原表情
        # 从右往左贴，让左边的脸压在右边的脸上面，和原图一致
        for img, (x, y, r) in reversed(list(zip(imgs, FACES))):
            face = img.convert("RGBA").square().resize((r * 2, r * 2)).circle()
            bg.paste(face, (x - r, y - r), alpha=True)
        bg.paste(front, alpha=True)
        return bg

    return make_jpg_or_gif(images, make)


add_meme(
    "queue_fuck",
    queue_fuck,
    min_images=1,
    max_images=5,
    min_texts=0,
    max_texts=1,
    default_texts=["我干死你"],
    args_type=args_type,
    keywords=["排队撅"],
    date_created=datetime(2026, 11, 1),
    date_modified=datetime(2026, 11, 1),
)
