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

项目只提供一份使用可变字体的 CSS：

```css
@import url("./index.css");
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
.venv/Scripts/python scripts/generate-fonts.py
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

- `KaimingPunctuation-VF.zip`：全部 OTF、TTF、WOFF2 可变字体及 `index.css`。
- `KaimingPunctuation-OTFs.zip`：全部静态 OTF。
- `KaimingPunctuation-WOFF2.zip`：全部静态 WOFF2。

每个归档均包含 README、FONTLOG 和 OFL 文本。分包内部不再重复格式分类，所有字体均直接放在 `fonts/` 下；三个归档中只有可变字体包包含 `index.css`。

## Cloudflare Workers Static Assets / Pages

构建会重新生成并校验字体，再把 `index.css`、两份可变 WOFF2、许可证和在线样张整理到 `public/`。同一套资源会同时发布在根路径和 `public/kaiming/`，以兼容 `workers.dev` 根地址及自定义域名的 `/kaiming/` 子路径：

```sh
python -m pip install -r requirements.txt
pnpm run build:pages
```

在 Cloudflare Pages 的 Git 构建设置中使用：

```text
Build command: python -m pip install -r requirements.txt && pnpm run build:pages
Build output directory: public
```

如果项目部署地址是 `*.workers.dev`，说明它使用 Workers Static Assets。仓库中的 `wrangler.jsonc` 会明确把完整的 `public/` 作为资源目录；在 Workers Builds 中使用：

```text
Build command: python -m pip install -r requirements.txt && pnpm run build:pages
Deploy command: pnpm exec wrangler deploy
```

不要在 Workers Builds 中另行指定单个 HTML 文件或仓库根目录作为静态资源目录，否则嵌套的 `fonts/variable/*.woff2` 不会随部署上传。

仓库有意不在 `wrangler.jsonc` 中保存域名或 Worker Routes。若要把站点挂载到自定义主机的 `/kaiming/` 下，请在 Cloudflare Dashboard 的 **Worker → Settings → Domains & Routes → Add → Route** 中手动添加：

```text
<host>/kaiming
<host>/kaiming/*
```

`<host>` 必须在 Cloudflare DNS 中存在并开启代理（橙色云）。部署后可从自定义域名引入：

```css
@import url("https://<host>/kaiming/index.css");
```

对应字体文件为 `https://<host>/kaiming/Sans-VF.woff2` 和 `Serif-VF.woff2`。`workers_dev` 保持启用，因此 `*.workers.dev` 根路径仍可访问。域名和 Route 由 Dashboard 管理，后续执行 `wrangler deploy` 不会把个人域名写入仓库。

建议固定构建环境变量 `NODE_VERSION=24`、`PYTHON_VERSION=3.13` 和 `PNPM_VERSION=10.33.2`。使用传统 Pages 项目时，也可直接跨域引入：

```css
@import url("https://<project>.pages.dev/index.css");
```

`pages/_headers` 会为托管文件提供跨域访问及缓存响应头；同名字体文件可能随版本更新，因此没有设置长期 `immutable` 缓存。

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

完整许可文本见 [`LICENSE`](LICENSE)，修改记录见 [`FONTLOG.txt`](FONTLOG.txt)。
