#!/usr/bin/env python3
"""
markdown → 微信公众号 HTML 转换引擎

根据文章内容匹配最佳排版风格，输出符合微信公众号渲染规范的 HTML。
所有样式内联，仅使用微信白名单标签。

用法:
  python3 scripts/wechat-format.py input.md [--style ink|azure|cinnabar] [output.html]

如果不指定 --style，脚本会基于内容分析自动推荐。
"""

import sys
import os
import re
import math
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from html import escape as html_escape


# ═══════════════════════ 风格配置文件 ═══════════════════════

PROFILES = {}

# ── 1. 随笔·温墨 (Ink) ──
# 适合：个人随笔、散文、叙事、小说
PROFILES["ink"] = {
    "name": "温墨",
    "emoji": "📝",
    "description": "暖色系，适合随笔、散文、叙事类文章。雅致、留白通透",
    "color": {
        "accent":       "#8B6914",  # 琥珀棕
        "accent_light": "#FDF6EC",  # 暖白
        "text":         "#3D3D3D",  # 深灰
        "text_secondary": "#7A7A7A",
        "border":       "#E8E0D0",  # 暖灰
        "bg_light":     "#FAF8F5",  # 暖白底
        "bg_code":      "#F5F3EF",
    },
    "font": {
        "body": "17px",
        "small": "14px",
        "h1": "24px",
        "h2": "20px",
        "h3": "18px",
        "h4": "17px",
        "code": "14px",
    },
    "line_height": "1.85",
    "style": {
        "h1": {"text-align": "center", "letter-spacing": "2px", "font-weight": "normal", "margin-top": "24px", "margin-bottom": "20px"},
        "h2": {"border-left": "3px solid", "font-weight": "normal", "padding-left": "16px", "margin-top": "32px", "margin-bottom": "14px"},
        "blockquote": {"border-left": "3px solid", "font-style": "italic", "padding": "14px 18px"},
        "hr": {"opacity": "0.3"},
    },
}

# ── 2. 教程·青蓝 (Azure) ──
# 适合：技术教程、指南、方法论、干货
PROFILES["azure"] = {
    "name": "青蓝",
    "emoji": "🔷",
    "description": "清爽蓝调，适合教程、技术文章。结构清晰、功能性强",
    "color": {
        "accent":       "#2B6CB0",
        "accent_light": "#EBF4FF",
        "text":         "#333333",
        "text_secondary": "#666666",
        "border":       "#E8E8E8",
        "bg_light":     "#F7F8FA",
        "bg_code":      "#F5F6F7",
    },
    "font": {
        "body": "16px",
        "small": "14px",
        "h1": "22px",
        "h2": "19px",
        "h3": "17px",
        "h4": "16px",
        "code": "13px",
    },
    "line_height": "1.75",
    "style": {
        "h1": {"text-align": "center", "letter-spacing": "1px", "font-weight": "bold"},
        "h2": {"border-left": "4px solid", "font-weight": "bold", "padding-left": "14px"},
        "h3": {"font-weight": "bold"},
        "blockquote": {"border-left": "4px solid", "padding": "12px 16px"},
        "hr": {"opacity": "0.5"},
        "th": {"background-color": None, "font-weight": "bold"},  # th uses accent as bg
    },
}

# ── 3. 评论·赤丹 (Cinnabar) ──
# 适合：观点文章、评论、深度分析、檄文
PROFILES["cinnabar"] = {
    "name": "赤丹",
    "emoji": "🔥",
    "description": "朱红醒目，适合观点文、评论。对比强、有力量感",
    "color": {
        "accent":       "#C0392B",  # 朱红
        "accent_light": "#FDF0EF",
        "text":         "#2D2D2D",
        "text_secondary": "#6B6B6B",
        "border":       "#E0D0D0",
        "bg_light":     "#F9F5F4",
        "bg_code":      "#F4F0EF",
    },
    "font": {
        "body": "17px",
        "small": "14px",
        "h1": "24px",
        "h2": "20px",
        "h3": "18px",
        "h4": "17px",
        "code": "14px",
    },
    "line_height": "1.8",
    "style": {
        "h1": {"text-align": "center", "letter-spacing": "1px", "font-weight": "bold", "margin-bottom": "24px"},
        "h2": {"border-left": "4px solid", "font-weight": "bold", "padding-left": "14px"},
        "h3": {"font-weight": "bold"},
        "blockquote": {"border-left": "4px solid", "font-weight": "bold", "padding": "16px 20px", "font-size": "18px"},
        "hr": {"opacity": "0.4"},
        "strong": {"font-weight": "bold"},
    },
}


def get_color(p, key):
    return PROFILES[p]["color"].get(key, "#333333")


def get_font(p, key):
    return PROFILES[p]["font"].get(key, "16px")


def istyle(props):
    return "; ".join(f"{k}: {v}" for k, v in props.items() if v is not None)


def tag_style(profile, tag):
    """对指定 profile 和 tag 生成完整的 inline style 字符串。"""
    p = PROFILES[profile]
    c = p["color"]
    base = {
        "font-size": get_font(profile, tag) if tag in ("h1","h2","h3","h4","h5","h6","body","small","code") else None,
    }
    
    # 各标签基础样式
    if tag == "h1":
        base.update({
            "color": c["text"],
            "font-weight": "bold",
            "text-align": "center",
            "margin": "20px 0 16px 0",
            "line-height": "1.6",
            "letter-spacing": "1px",
            "font-size": get_font(profile, "h1"),
        })
    elif tag == "h2":
        base.update({
            "color": c["accent"],
            "font-weight": "bold",
            "margin": "28px 0 12px 0",
            "padding": "0 0 0 14px",
            "border-left": f"4px solid {c['accent']}",
            "line-height": "1.6",
            "font-size": get_font(profile, "h2"),
        })
    elif tag == "h3":
        base.update({
            "color": c["text"],
            "font-weight": "bold",
            "margin": "22px 0 10px 0",
            "line-height": "1.6",
            "font-size": get_font(profile, "h3"),
        })
    elif tag == "h4":
        base.update({
            "color": c["text_secondary"],
            "font-weight": "bold",
            "margin": "18px 0 8px 0",
            "line-height": "1.6",
        })
    elif tag == "p":
        base.update({
            "color": c["text"],
            "line-height": p["line_height"],
            "letter-spacing": "0.5px",
            "margin": "0 0 14px 0",
            "font-size": get_font(profile, "body"),
        })
    elif tag == "blockquote":
        base.update({
            "color": c["text_secondary"],
            "line-height": p["line_height"],
            "margin": "18px 0",
            "padding": "12px 18px",
            "border-left": f"4px solid {c['accent']}",
            "background-color": c["bg_light"],
            "font-size": get_font(profile, "body"),
        })
    elif tag == "pre":
        base.update({
            "font-size": get_font(profile, "code"),
            "line-height": "1.6",
            "margin": "16px 0",
            "padding": "16px 18px",
            "background-color": c["bg_code"],
            "border-radius": "6px",
            "overflow-x": "auto",
            "font-family": "Consolas, 'Liberation Mono', Menlo, Courier, monospace",
        })
    elif tag == "code":
        base.update({
            "font-size": "13px",
            "padding": "2px 6px",
            "background-color": c.get("accent_light", "#EDF2F7"),
            "border-radius": "3px",
            "font-family": "Consolas, 'Liberation Mono', Menlo, Courier, monospace",
            "color": c["accent"],
        })
    elif tag in ("ul", "ol"):
        base.update({
            "font-size": get_font(profile, "body"),
            "color": c["text"],
            "line-height": p["line_height"],
            "margin": "8px 0 14px 0",
            "padding-left": "24px",
        })
    elif tag == "li":
        base.update({
            "font-size": get_font(profile, "body"),
            "color": c["text"],
            "line-height": p["line_height"],
            "margin": "4px 0",
        })
    elif tag == "a":
        base.update({
            "color": c["accent"],
            "text-decoration": "none",
            "border-bottom": f"1px solid {c['accent']}",
        })
    elif tag == "img":
        base.update({
            "max-width": "100%",
            "height": "auto",
            "display": "block",
            "margin": "16px auto",
            "border-radius": "4px",
        })
    elif tag == "hr":
        base.update({
            "margin": "24px 0",
            "border": "none",
            "border-top": f"1px solid {c['border']}",
        })
    elif tag == "table":
        base.update({
            "font-size": "15px",
            "color": c["text"],
            "line-height": "1.6",
            "margin": "16px 0",
            "border-collapse": "collapse",
            "width": "100%",
        })
    elif tag == "th":
        base.update({
            "padding": "10px 14px",
            "border": f"1px solid {c['border']}",
            "background-color": c["accent"],
            "color": "#FFFFFF",
            "font-weight": "bold",
            "text-align": "center",
            "font-size": "15px",
        })
    elif tag == "td":
        base.update({
            "padding": "8px 14px",
            "border": f"1px solid {c['border']}",
            "text-align": "left",
            "font-size": "15px",
        })
    elif tag == "strong":
        base.update({
            "color": c["accent"],
            "font-weight": "bold",
        })
    elif tag == "em":
        base.update({"font-style": "italic"})
    elif tag == "s":
        base.update({"text-decoration": "line-through", "color": c["text_secondary"]})
    elif tag == "u":
        base.update({"text-decoration": "underline"})
    
    return istyle({k: v for k, v in base.items() if v is not None})


# ═══════════════════════ 内容分析 ═══════════════════════

def analyze_content(md_text: str) -> str:
    """分析 Markdown 内容，推荐最佳风格 profile。"""
    lines = md_text.split("\n")
    total_chars = len(md_text)
    
    # 统计特征
    code_blocks = len(re.findall(r'^```', md_text, re.MULTILINE)) // 2
    blockquotes = len(re.findall(r'^>', md_text, re.MULTILINE))
    headings = len(re.findall(r'^#{1,6} ', md_text, re.MULTILINE))
    h1_count = len(re.findall(r'^# ', md_text, re.MULTILINE))
    lists = len(re.findall(r'^[-*+] |^\d+\. ', md_text, re.MULTILINE))
    tables = len(re.findall(r'^\|.+\|$', md_text, re.MULTILINE))
    
    # 关键词检测
    text_lower = md_text.lower()
    
    # 技术类关键词
    tech_keywords = ["代码", "函数", "api", "python", "安装", "配置", "部署", "github",
                     "命令", "教程", "步骤", "方法", "实现", "server", "client", "数据库",
                     "vue", "react", "docker", "kubernetes", "cli", "terminal",
                     "安装", "下载", "运行", "npm", "git", "http", "url", "json"]
    
    # 观点类关键词（强表态词）
    opinion_keywords = ["为什么", "但我认为", "我建议", "不值得", "别再", "警惕",
                        "真相", "反思", "批判", "我反对", "我不同意", "说实话",
                        "说真的", "醒醒", "别再骗", "别再被", "千万别"]
    
    # 叙事类关键词（第一人称经历、回忆、感受）
    narrative_keywords = ["记得", "那时候", "小时候", "想起", "感觉", "也许",
                          "可能", "后来", "曾经", "回忆", "我", "我的",
                          "我们", "那天", "那年", "有一次"]
    
    # 强叙事信号（整句表达个人经历）
    narrative_phrases = ["我见过", "我去过", "我做过", "我经历过", "我遇到",
                         "我记得", "我小时候", "那一年", "有一次", "那时候"]
    
    tech_score = sum(2 for kw in tech_keywords if kw in text_lower)
    opinion_score = sum(2 for kw in opinion_keywords if kw in text_lower)
    narrative_score = sum(1 for kw in narrative_keywords if kw in text_lower)
    narrative_score += sum(3 for kw in narrative_phrases if kw in text_lower)
    
    # 结构特征加权
    tech_score += code_blocks * 8        # 代码块很强地指向技术文
    tech_score += tables * 3
    tech_score += lists * 1
    opinion_score += blockquotes * 2     # 引用在观点文中常见
    
    # 叙事文通常有更长的段落、更多第一人称、更少结构化元素
    # 如果代码块为0且技术词少，加权叙事
    
    # 决定
    if code_blocks >= 1 and tech_score >= max(opinion_score, narrative_score):
        return "azure"
    elif opinion_score >= 5 and opinion_score > narrative_score:
        return "cinnabar"
    elif narrative_score >= opinion_score and narrative_score >= tech_score:
        return "ink"
    else:
        # 正文内容比例高 → ink，结构性强 → azure
        structural_ratio = (code_blocks + headings + lists + tables) / max(total_chars, 1) * 1000
        if structural_ratio > 5:
            return "azure"
        return "ink"


# ═══════════════════════ HTML 渲染 ═══════════════════════

def format_code(code: str, lang: str = "") -> str:
    try:
        if lang:
            lexer = get_lexer_by_name(lang, stripall=True)
        else:
            lexer = guess_lexer(code)
    except Exception:
        lexer = None
    if lexer:
        formatter = HtmlFormatter(nowrap=True, style="friendly", noclasses=True)
        return highlight(code, lexer, formatter)
    return html_escape(code)


def convert(md_text: str, profile: str = "azure", title: str = "") -> str:
    md = MarkdownIt("default", {"breaks": True, "html": True, "linkify": False, "typographer": True})
    raw_html = md.render(md_text)
    c = PROFILES[profile]["color"]
    
    def ts(tag):
        return tag_style(profile, tag)
    
    def add_style(pattern, repl_func):
        nonlocal raw_html
        raw_html = re.sub(pattern, repl_func, raw_html)
    
    # 代码块 语法高亮
    def replace_code(m):
        lang = m.group(1) or ""
        code = m.group(2).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        highlighted = format_code(code, lang)
        return f'<pre style="{ts("pre")}"><code style="{ts("code")}">{highlighted}</code></pre>'
    
    raw_html = re.sub(
        r'<pre><code class="language-(\w*)">(.*?)</code></pre>',
        replace_code, raw_html, flags=re.DOTALL
    )
    
    # 内联代码
    raw_html = re.sub(
        r'<code>(?!\s)(.*?)(?<!\s)</code>',
        lambda m: f'<code style="{ts("code")}">{m.group(1)}</code>',
        raw_html,
    )
    
    # === 为各种标签添加内联样式 ===
    # 按顺序处理，避免互相干扰
    
    # 表格
    raw_html = re.sub(r'<table>', f'<table style="{ts("table")}">', raw_html)
    raw_html = re.sub(r'<th(?![^>]*style=)>', f'<th style="{ts("th")}">', raw_html)
    raw_html = re.sub(r'<td(?![^>]*style=)>', f'<td style="{ts("td")}">', raw_html)
    
    # 自闭合标签
    raw_html = re.sub(r'<hr>', f'<hr style="{ts("hr")}" />', raw_html)
    raw_html = re.sub(r'<img(?![^>]*style=)([^>]*)>',
        lambda m: f'<img style="{ts("img")}" {m.group(1)}>', raw_html)
    
    # 标题
    for level in range(1, 7):
        tag = f"h{level}"
        raw_html = re.sub(f'<{tag}(?![^>]*style=)([^>]*)>',
            lambda m, t=tag: f'<{t} style="{ts(t)}" {m.group(1)}>', raw_html)
    
    # 段落 + 块级
    for tag in ["p", "blockquote", "pre"]:
        raw_html = re.sub(f'<{tag}(?![^>]*style=)([^>]*)>',
            lambda m, t=tag: f'<{t} style="{ts(t)}" {m.group(1)}>', raw_html)
    
    # 列表
    for tag in ["ul", "ol"]:
        raw_html = re.sub(f'<{tag}(?![^>]*style=)([^>]*)>',
            lambda m, t=tag: f'<{t} style="{ts(t)}" {m.group(1)}>', raw_html)
    raw_html = re.sub(r'<li(?![^>]*style=)([^>]*)>',
        lambda m: f'<li style="{ts("li")}" {m.group(1)}>', raw_html)
    
    # 内联标签（注意词边界避免误伤）
    inline_tags = [
        (r'<(strong|b)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "strong"),
        (r'<(em|i)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "em"),
        (r'<(s|del)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "s"),
        (r'<u(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "u"),
        (r'<a(?![^>]*style=)([^>]*)>', "a"),
    ]
    for pattern, tagname in inline_tags:
        raw_html = re.sub(pattern,
            lambda m, t=tagname: f'<{m.group(1) if m.lastindex and m.lastindex >= 2 and m.group(2) is not None else tagname} style="{ts(t)}" {m.group(m.lastindex)}>',
            raw_html)
    
    # 清理不需要的空白
    raw_html = re.sub(r'\n{3,}', '\n\n', raw_html)
    
    # 最终包装
    p = PROFILES[profile]
    title_html = f'<h1 style="{ts("h1")}">{html_escape(title)}</h1>\n' if title else ""
    
    output = f"""<section style="max-width: 677px; margin: 0 auto; padding: 10px 16px; font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;">
{title_html}
{raw_html.strip()}
</section>"""
    
    return output


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Markdown → 微信公众号 HTML")
    parser.add_argument("input", help="输入的 Markdown 文件路径")
    parser.add_argument("output", nargs="?", help="输出的 HTML 文件路径（可选）")
    parser.add_argument("--style", choices=list(PROFILES.keys()), default=None,
                        help="排版风格（ink/azure/cinnabar），不指定则自动分析")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 文件不存在: {args.input}")
        sys.exit(1)
    
    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()
    
    # 提取 YAML frontmatter 标题
    title = ""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", md_text, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        t_match = re.search(r"^title:\s*['\"]?(.+?)['\"]?$", fm_text, re.MULTILINE)
        if t_match:
            title = t_match.group(1).strip()
        md_text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", md_text, flags=re.DOTALL, count=1)
    
    # 分析内容 → 选择风格
    chosen = args.style or analyze_content(md_text)
    
    output_html = convert(md_text, profile=chosen, title=title)
    
    if args.output:
        out_path = args.output
    else:
        base, _ = os.path.splitext(args.input)
        out_path = f"{base}.wechat.html"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
    p = PROFILES[chosen]
    print(f"✅ 已生成: {out_path}")
    print(f"   风格: {p['emoji']} {p['name']} — {p['description']}")
    print(f"   文章长度: {len(output_html)} 字符")
    print(f"   用法: 用浏览器打开 HTML → 全选复制 → 粘贴到微信编辑器")


if __name__ == "__main__":
    main()
