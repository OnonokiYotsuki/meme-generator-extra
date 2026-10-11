# `meme-generator` 额外表情仓库

此仓库为 表情包生成器 [meme-generator](https://github.com/MemeCrafters/meme-generator) 的个人额外表情仓库，结构参照 [meme-generator-contrib](https://github.com/MemeCrafters/meme-generator-contrib)

适用于 Python 版 `meme-generator`（0.1.x）

## 表情列表

| 关键词 | 名称 | 图片数 | 选项 |
| ------ | ---- | ------ | ---- |
| 猫摇 | `neko_shake` | 1 | `--circle` / `圆`：将图片变为圆形 |

## 使用方式

参考 [`meme-generator` 加载其他表情的方式](https://github.com/MemeCrafters/meme-generator/wiki/%E5%8A%A0%E8%BD%BD%E5%85%B6%E4%BB%96%E8%A1%A8%E6%83%85)

在 `meme_generator` 的配置文件 `config.toml` 中添加本仓库的 `memes` 目录：

```toml
[meme]
meme_dirs = ["D:/Code/Bots/meme-generator-extra/memes"]
```

## 添加新表情

在 `memes/` 下新建一个以表情名命名的文件夹，包含：

```
memes/<meme_name>/
├── __init__.py   # 表情函数，并调用 add_meme 注册
└── images/       # 表情所用素材
```

素材路径统一写成 `Path(__file__).parent / "images"`

## 声明

本仓库的表情素材等均来自网络，如有侵权请联系作者删除
