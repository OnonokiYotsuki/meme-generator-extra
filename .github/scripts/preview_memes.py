"""为 PR 中新增/修改的表情生成预览图。

用法：
    python preview_memes.py --out preview --image-url-prefix <url> memes/a memes/b ...

在 ``--out`` 目录下输出：
    - 预览图片（<key>.gif / <key>_instance0.png ...）
    - comment.md   PR 评论内容
    - result.json  机器可读结果（ok: 是否全部成功）
"""

import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import filetype
from meme_generator.compat import model_dump
from meme_generator.manager import _memes
from meme_generator.meme import Meme
from meme_generator.utils import random_image, random_text

MAX_PREVIEW_IMAGES = 9


def load_meme_dir(path: Path) -> tuple[list[str], str]:
    """加载单个表情目录，返回 (新注册的表情 key 列表, 错误信息)。"""
    init_file = path / "__init__.py"
    if not init_file.exists():
        return [], f"`{path}` 下没有 `__init__.py`"
    before = set(_memes)
    spec = importlib.util.spec_from_file_location(
        path.name, init_file, submodule_search_locations=[str(path)]
    )
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return [], traceback.format_exc()
    keys = [key for key in _memes if key not in before]
    if not keys:
        return [], "模块导入成功，但没有调用 `add_meme` 注册任何表情（或 key 重复）"
    return keys, ""


def generate(
    meme: Meme, image_num: int, args: dict[str, Any]
) -> tuple[bytes, list[str]]:
    params = meme.params_type
    images = [random_image() for _ in range(image_num)]
    if params.min_texts <= len(params.default_texts) <= params.max_texts:
        texts = params.default_texts.copy()
    else:
        texts = [random_text() for _ in range(params.min_texts)]
    for _ in range(10):
        try:
            result = meme(images=images, texts=texts, args=args)
            return result.getvalue(), texts
        except Exception as e:
            if type(e).__name__ == "TextOrNameNotEnough":
                texts.append(random_text())
                continue
            raise
    raise RuntimeError("补充文字后仍无法生成")


def meme_info(meme: Meme) -> str:
    p = meme.params_type
    image_num = f"{p.min_images}" + (
        f" ~ {p.max_images}" if p.max_images > p.min_images else ""
    )
    text_num = f"{p.min_texts}" + (
        f" ~ {p.max_texts}" if p.max_texts > p.min_texts else ""
    )
    lines = [
        f"- 关键词：{'、'.join(f'`{k}`' for k in meme.keywords) or '无'}",
        f"- 需要图片数目：`{image_num}`",
        f"- 需要文字数目：`{text_num}`",
    ]
    if p.default_texts:
        lines.append(f"- 默认文字：{'、'.join(f'`{t}`' for t in p.default_texts)}")
    if meme.shortcuts:
        shortcuts = "、".join(f"`{s.humanized or s.key}`" for s in meme.shortcuts)
        lines.append(f"- 快捷指令：{shortcuts}")
    if meme.tags:
        lines.append(f"- 标签：{'、'.join(f'`{t}`' for t in sorted(meme.tags))}")
    return "\n".join(lines)


def build_cases(meme: Meme) -> list[tuple[str, str, int, dict[str, Any]]]:
    """返回 (文件名, 说明, 图片数, 参数) 列表。"""
    p = meme.params_type
    cases: list[tuple[str, str, int, dict[str, Any]]] = []
    examples = p.args_type.args_examples if p.args_type else []
    if examples:
        for i, example in enumerate(examples):
            args = model_dump(example)
            shown = json.dumps(
                {k: v for k, v in args.items() if k != "user_infos"},
                ensure_ascii=False,
            )
            cases.append(
                (f"{meme.key}_instance{i}", f"参数：`{shown}`", p.min_images, args)
            )
    else:
        cases.append((meme.key, "默认", p.min_images, {}))
    max_images = min(p.max_images, MAX_PREVIEW_IMAGES)
    if max_images > p.min_images:
        cases.append((f"{meme.key}_max_images", f"{max_images} 张图片", max_images, {}))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--image-url-prefix", default="")
    parser.add_argument("dirs", nargs="*", type=Path)
    opts = parser.parse_args()

    out: Path = opts.out
    out.mkdir(parents=True, exist_ok=True)
    prefix: str = opts.image_url_prefix

    ok = True
    sections: list[str] = []
    generated: list[str] = []

    for meme_dir in opts.dirs:
        keys, error = load_meme_dir(meme_dir)
        if error:
            ok = False
            sections.append(
                f"### ❌ `{meme_dir}`\n\n加载失败：\n\n```\n{error.strip()}\n```"
            )
            continue
        for key in keys:
            meme = _memes[key]
            rows: list[str] = []
            errors: list[str] = []
            for name, desc, image_num, args in build_cases(meme):
                try:
                    content, texts = generate(meme, image_num, args)
                except Exception:
                    errors.append(
                        f"**{desc}**\n\n```\n{traceback.format_exc().strip()}\n```"
                    )
                    continue
                ext = filetype.guess_extension(content) or "png"
                filename = f"{name}.{ext}"
                (out / filename).write_bytes(content)
                generated.append(filename)
                text_desc = (
                    f"，文字：{'、'.join(f'`{t}`' for t in texts)}" if texts else ""
                )
                img = f'<img src="{prefix}{filename}" height="200">'
                rows.append(f"| {desc}（{image_num} 张图{text_desc}） | {img} |")
            status = "❌" if errors else "✅"
            ok = ok and not errors
            body = f"### {status} `{key}`（`{meme_dir}`）\n\n{meme_info(meme)}\n"
            if rows:
                body += "\n| 用例 | 预览 |\n| --- | --- |\n" + "\n".join(rows) + "\n"
            if errors:
                body += "\n生成失败：\n\n" + "\n\n".join(errors) + "\n"
            sections.append(body)

    if not opts.dirs:
        sections.append("这个 PR 没有新增或修改表情。")

    header = "## 表情预览 " + ("✅" if ok else "❌") + "\n\n"
    header += "使用占位图片和文字自动生成，每次推送后会更新。\n\n"
    (out / "comment.md").write_text(header + "\n\n".join(sections) + "\n", "utf-8")
    (out / "result.json").write_text(
        json.dumps({"ok": ok, "images": generated}, ensure_ascii=False), "utf-8"
    )
    sys.stdout.write((out / "comment.md").read_text("utf-8"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
