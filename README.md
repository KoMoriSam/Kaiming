# Kaiming

一套用于网页中文排版的开明式标点字体，以及可复现的字体生成和发布脚本。

项目从 Noto Sans SC 和 Noto Serif SC 提取标点字形，为无衬线和衬线正文分别生成 100–900 九档静态字重及一份可变字体。字体包含半宽标点、连续句末标点压缩、双破折号连字等排版规则。

静态字体只从 `@fontsource/noto-sans-sc` 和 `@fontsource/noto-serif-sc` 提取轮廓；可变字体只从对应的 `@fontsource-variable` 包生成。Noto Serif SC 上游没有 100 字重，因此其 Thin 轮廓由同一来源中拓扑兼容的 200/300 轮廓作线性外推，构建时会校验轮廓点数、端点及曲线类型。

## 字体产物

产物按用途和格式分类：

```text
fonts/
├── variable/
│   ├── kaiming-{sans,serif}-variable.ttf
│   ├── kaiming-{sans,serif}-variable.woff2
│   └── kaiming-{sans,serif}-variable.otf
└── static/
    ├── otf/   # 两个家族各 9 个静态 CFF OTF
    └── woff2/ # 两个家族各 9 个静态 TrueType WOFF2
```

合计 42 个字体文件。每份可变字体都包含 `wght` 100–900 连续轴、九个命名字重实例、对应的 `STAT AxisValue` 记录以及各实例独立的 PostScript 名称。

Windows 本地安装和字体查看器优先使用 `fonts/variable/*.ttf`。WOFF2 用于网页；CFF2 OTF 提供给支持 CFF2 可变轮廓的软件。

## 网页使用

静态字体：

```css
@import url("./kaiming-punctuation.css");
```

可变字体：

```css
@import url("./kaiming-punctuation-variable.css");
```

CSS 提供以下字体族：

- `Kaiming Punctuation Sans`
- `Kaiming Punctuation Serif`

字体元数据同时包含简体中文本地化家族名 `开明标点黑` 和 `开明标点宋`，以及九档中文命名字重；英文环境仍使用上述英文名称。

把相应字体族放在正文完整字体之前即可；`unicode-range` 会让它只接管所含标点。

## 本地构建

需要 Node.js、pnpm 10、Python 3.10 或更高版本：

```sh
pnpm install --frozen-lockfile
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/generate-kaiming-punctuation.py
```

在 macOS 或 Linux 上，将最后两条命令中的 `.venv/Scripts/python` 改为 `.venv/bin/python`。生成器会构建并重新打开校验全部 42 个文件，包括：

- OpenType 轮廓格式、可变轴、命名实例、实例 PostScript 名称及完整 `STAT` 字重记录；
- 字符集、字宽、标点间距和 OpenType 排版规则；
- `nameID 0` 版权、`nameID 13` OFL 说明、`nameID 14` 许可证 URL。

## 创建分发包

先完成字体构建，再运行：

```sh
python scripts/package-release.py
```

`dist/` 中会生成三个固定名称的 ZIP 和 `SHA256SUMS`：

- `KaimingPunctuation-VF.zip`：全部 OTF、TTF、WOFF2 可变字体及变量 CSS。
- `KaimingPunctuation-OTFs.zip`：全部静态 OTF。
- `KaimingPunctuation-WOFF2.zip`：全部静态 WOFF2 及静态 CSS。

每个归档均包含 README、FONTLOG 和 OFL 文本。分包内部不再重复格式分类，所有字体均直接放在 `fonts/` 下；压缩包内 CSS 的字体 URL 也会同步指向该目录。

## GitHub Actions 与 Releases

推送及 pull request 会自动安装锁定依赖、重新构建和校验字体，并上传可下载的 Actions artifact。

推送形如 `v1.0.0` 的 tag 会执行同样的干净构建，并自动创建或更新对应 GitHub Release，上传上述三个 ZIP 和 SHA-256 校验文件：

```sh
git tag v1.0.0
git push origin v1.0.0
```

也可从 Actions 页面手动运行工作流，验证构建但不创建 Release。

## 字体许可

字体产物衍生自 Noto Sans SC 与 Noto Serif SC，并包含 Kaiming Punctuation 的修改，全部遵循 SIL Open Font License 1.1。原版权、Reserved Font Name 声明及修改版权同时写入字体元数据和许可文件。

完整许可文本见 [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt)，修改记录见 [`FONTLOG.txt`](FONTLOG.txt)。
