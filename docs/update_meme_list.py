from pathlib import Path
from typing import Any

import filetype
from arclet.alconna import TextFormatter
from meme_generator import get_memes
from meme_generator.meme import Meme
from pil_utils import BuildImage

memes = sorted(get_memes(), key=lambda meme: meme.key)

current_path = Path(__file__).parent
image_path = current_path / "images"
thumb_path = current_path / "thumbs"
md_path = current_path / "表情列表.md"

image_path.mkdir(exist_ok=True, parents=True)
thumb_path.mkdir(exist_ok=True, parents=True)


def generate_preview_images():
    for meme in memes:

        def generate_image(name: str, args: dict[str, Any] = {}):
            for path in image_path.iterdir():
                if name == path.stem:
                    return

            result = meme.generate_preview(args=args)
            content = result.getvalue()
            ext = filetype.guess_extension(content)
            filename = f"{name}.{ext}"
            with open(image_path / filename, "wb") as f:
                f.write(content)

            img = BuildImage.open(result)
            if img.width > 150:
                result_resized = img.convert("RGBA").resize_width(150).save_jpg()
            else:
                result_resized = img.save_jpg()
            content_resized = result_resized.getvalue()
            ext_resized = filetype.guess_extension(content_resized)
            filename_resized = f"{name}.{ext_resized}"
            with open(thumb_path / filename_resized, "wb") as f:
                f.write(content_resized)

        generate_image(meme.key)
        if args := meme.params_type.args_type:
            if examples := args.args_examples:
                for i, example in enumerate(examples):
                    generate_image(f"{meme.key}_instance{i}", example.dict())


def meme_doc(meme: Meme) -> str:
    keywords = "、".join([f"`{keyword}`" for keyword in meme.keywords])
    shortcuts = "、".join(
        [f'"{shortcut.humanized or shortcut.key}"' for shortcut in meme.shortcuts]
    )
    tags = "、".join([f'"{tag}"' for tag in sorted(meme.tags)])

    image_num = f"`{meme.params_type.min_images}`"
    if meme.params_type.max_images > meme.params_type.min_images:
        image_num += f" ~ `{meme.params_type.max_images}`"

    text_num = f"`{meme.params_type.min_texts}`"
    if meme.params_type.max_texts > meme.params_type.min_texts:
        text_num += f" ~ `{meme.params_type.max_texts}`"

    default_texts = (
        f"{', '.join([f'`{text}`' for text in meme.params_type.default_texts])}"
    )

    def arg_info(name: str, info: dict[str, Any]) -> str:
        text = (
            f"    - `{name}`\n"
            f"        - 描述：{info.get('description', '')}\n"
            f"        - 类型：`{info.get('type', '')}`\n"
            f"        - 默认值：`{info.get('default', '')}`"
        )
        if enum := info.get("enum", []):
            assert isinstance(enum, list)
            text += f"\n        - 可选值：{'、'.join([f'`{e}`' for e in enum])}"
        return text

    if args := meme.params_type.args_type:
        model = args.args_model
        properties: dict[str, dict[str, Any]] = (
            model.schema().get("properties", {}).copy()
        )
        properties.pop("user_infos")
        args_info = "\n" + "\n".join(
            [arg_info(name, info) for name, info in properties.items()]
        )
    else:
        args_info = ""

    parser_info = ""
    if args_type := meme.params_type.args_type:
        formater = TextFormatter()
        for option in args_type.parser_options:
            opt = option.option()
            alias_text = (
                " ".join(opt.requires)
                + (" " if opt.requires else "")
                + "│".join(sorted(opt.aliases, key=len))
            )
            parser_info += (
                f"    - {alias_text}{opt.separators[0]}"
                f"{formater.parameters(opt.args)} {opt.help_text}\n"
            )

    def image_doc(name: str) -> str:
        img_path = Path()
        tmb_path = Path()
        for path in image_path.iterdir():
            if name == path.stem:
                img_path = path.relative_to(current_path)
        for path in thumb_path.iterdir():
            if name == path.stem:
                tmb_path = path.relative_to(current_path)
        return f"[![]({tmb_path})]({img_path})"

    preview_image = ""
    if args := meme.params_type.args_type:
        if examples := args.args_examples:
            preview_image = "\n\n".join(
                [
                    f"> 参数：{example.json(exclude={'user_infos'})}\n\n"
                    + image_doc(meme.key + f"_instance{i}")
                    for i, example in enumerate(examples)
                ]
            )
    if not preview_image:
        preview_image = image_doc(meme.key)

    return (
        f"## {meme.key}\n\n"
        + f"- 关键词：{keywords}\n"
        + (f"- 快捷指令：{shortcuts}\n" if shortcuts else "")
        + (f"- 标签：{tags}\n" if tags else "")
        + f"- 需要图片数目：{image_num}\n"
        + f"- 需要文字数目：{text_num}\n"
        + (f"- 默认文字：[{default_texts}]\n" if default_texts else "")
        + (f"- 其他参数：{args_info}\n" if args_info else "")
        + (f"- 其他参数（命令行选项）：\n{parser_info}\n" if parser_info else "")
        + "- 预览：（点击图片查看原图）\n\n"
        + f"{preview_image}"
    )


def generate_toc():
    return "\n".join(
        f"{i}. [{meme.key} ({'/'.join(meme.keywords)})](#{meme.key})"
        for i, meme in enumerate(memes, start=1)
    )


def generate_doc():
    doc = "以下为表情的关键词、所需参数等信息及表情预览\n\n按照表情的 `key` 排列\n\n\n"
    doc += generate_toc() + "\n\n\n"
    doc += "\n\n".join(meme_doc(meme) for meme in memes) + "\n"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(doc)


def main():
    generate_preview_images()
    generate_doc()


if __name__ == "__main__":
    main()
