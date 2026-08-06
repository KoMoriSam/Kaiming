# Kaiming Punctuation v1.1.0

本版本扩充了字体字符集和标点排版规则，并将网页 CSS 入口统一为
`index.css`。

## 新增字符

- 间隔号 `·`（U+00B7）：固定半字宽。
- 半字连接号 `–`（U+2013）、斜线 `/`（U+002F）和竖线 `|`
  （U+007C）：固定半字宽。
- 四分空格（U+2005）：四分之一字宽。
- 二分空格（U+2002）：半字宽。
- 全宽空格（U+3000）：全字宽。

## 字形与排版调整

- `·`、`–`、`/`、`|` 按真实轮廓水平居中，并与破折号统一对齐至
  CJK 视觉中线。
- 双破折号 `——` 继续合成为连续二字宽 `ccmp` 连字。
- 双破折号连字左右外边距由 `0.1 em` 缩减至 `0.05 em`。
- 改用真实曲线边界计算视觉中心，并加强静态字体和变量字体的布局校验。
- 完善无轮廓空格在衬线 Thin 外推和轮廓签名校验中的处理。

## CSS 与发布

- CSS 统一为单一入口 `index.css`，包含两个 100–900 可变字体
  `@font-face`。
- `unicode-range` 已与字体 cmap 的全部 40 个码位同步。
- 在线样张、缓存响应头、README、页面构建及下载链接均改用
  `index.css`。
- 三个 Release ZIP 中仅可变字体包包含 `index.css`；静态 OTF 和
  WOFF2 包不再包含 CSS。
- 字体生成脚本更名为 `scripts/generate-fonts.py`。

## 兼容性变更

旧 CSS 文件 `kaiming-punctuation.css` 和
`kaiming-punctuation-variable.css` 已移除，请改用：

```css
@import url("./index.css");
```

本版本包含两套字族、九档静态字重及 100–900 可变字重，共 42 个经过
重新生成和验证的 OTF、TTF、WOFF2 字体文件。
