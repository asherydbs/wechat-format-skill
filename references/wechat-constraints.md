# 微信公众号渲染约束（速查）

来源：`raw/papers/wechat-rendering-engine-report.md`（AI 调研生成，部分细节需交叉验证）

## CSS

| 特性 | 状态 | 说明 |
|------|------|------|
| 内联样式 | ✅ 必须 | 所有样式写入 `style` 属性 |
| `<style>` 标签 | ❌ 过滤 | 不支持 class/ID 选择器 |
| 外部 CSS (`<link>`) | ❌ 过滤 | |
| `position` | ❌ 无效 | absolute/fixed/relative 均被过滤 |
| `flexbox` | ❌ 基本不支持 | 行为不可靠 |
| `grid` | ❌ 不支持 | |
| `float` | ⚠️ 部分支持 | 可用于简单文字环绕，复杂嵌套不稳定 |
| CSS 动画/过渡 | ❌ 过滤 | `@keyframes`, `transition` 无效 |
| CSS 变量 | ❌ 过滤 | `--var` / `var()` 无效 |
| `border-radius` | ✅ 支持 | 圆角可用 |

## HTML 标签

### 支持
`div`, `span`, `p`, `br`, `h1`-`h6`, `strong`, `em`, `u`, `del`, `b`, `i`, `ul`, `ol`, `li`, `blockquote`, `a`, `img`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `hr`, `pre`, `code`, `s`

### 禁用
`script`, `iframe`, `frame`, `frameset`, `style`, `link`, `form`, `input`, `textarea`, `button`, `select`, `meta`, `head`, `body`, `html`, `video`, `audio`, `source`

## 多媒体

| 类型 | 格式 | 大小限制 |
|------|------|----------|
| 图片 | JPG, PNG, GIF | 单张 ≤10MB（2026.3 起） |
| 图片（不支持） | WebP, SVG（文件） | WebP 无法上传；SVG 可以代码嵌入 |
| 视频 | MP4 最佳 | 直接上传 ≤20MB；超限用腾讯视频 |
| 音频 | MP3 最佳 | ≤5MB |

- 所有图片被微信转存到 `mmbiz.qpic.cn`
- 外链图片会被转存，防盗链图片无法显示
- 微信编辑器不支持 Markdown 原生语法

## 布局限制

无法使用绝对/固定定位。所有元素在正常文档流中从上到下排列。复杂布局需用 `<table>` 或多重 `<div>` 嵌套 + margin/padding 模拟。

## 工作流

```
外部编辑器写 Markdown → 转换工具（此 skill）→ 复制 HTML → 粘贴到微信编辑器 → 发布
```
