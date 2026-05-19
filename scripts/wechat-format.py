#!/usr/bin/env python3
"""
markdown → 微信公众号 HTML 转换引擎
根据文章内容匹配最佳排版风格，支持丰富排版组件。

用法:
  python3 scripts/wechat-format.py input.md [output.html] [--style ink|azure|cinnabar]

排版组件（在 markdown 中使用）:
  ::: card     卡片区块（圆角白底+微阴影）
  ::: highlight 重点高亮（主色调背景）
  ::: quote    金句引用（大字号+主色调）
  ::: tip      提示信息（左竖线+图标点）
  ::: section  装饰标题（背景色块式小标题）
"""

import sys, os, re
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from html import escape as html_escape


# ═══════ 色彩配置 ═══════
C = {
    "ink": {
        "accent":"#8B6914","alight":"#FDF6EC","text":"#3D3D3D","sec":"#7A7A7A",
        "border":"#E8E0D0","bg":"#FAF8F5","code":"#F5F3EF",
        "font_body":"17px","font_h1":"24px","font_h2":"20px","lh":"1.85",
        "emoji":"📝",
    },
    "azure": {
        "accent":"#2B6CB0","alight":"#EBF4FF","text":"#333333","sec":"#666666",
        "border":"#E8E8E8","bg":"#F7F8FA","code":"#F5F6F7",
        "font_body":"16px","font_h1":"22px","font_h2":"19px","lh":"1.75",
        "emoji":"🔷",
    },
    "cinnabar": {
        "accent":"#C0392B","alight":"#FDF0EF","text":"#2D2D2D","sec":"#6B6B6B",
        "border":"#E0D0D0","bg":"#F9F5F4","code":"#F4F0EF",
        "font_body":"17px","font_h1":"24px","font_h2":"20px","lh":"1.8",
        "emoji":"🔥",
    },
}


def pr(p, k, fallback=""):
    return C.get(p, {}).get(k, fallback)


def style(props):
    return "; ".join(f"{k}: {v}" for k,v in props.items() if v)


# ═══════ 组件样式 ═══════

def tag_style(profile, tag):
    c = C[profile]
    s = {}
    if tag == "h1":
        s.update({"font-size":c["font_h1"],"font-weight":"bold","color":c["text"],
                   "text-align":"center","margin":"20px 0 16px","line-height":"1.6","letter-spacing":"1px"})
    elif tag == "h2":
        s.update({"font-size":c["font_h2"],"font-weight":"bold","color":c["accent"],
                   "margin":"28px 0 12px","padding":"0 0 0 14px",
                   "border-left":f"4px solid {c['accent']}","line-height":"1.6"})
    elif tag == "h3":
        s.update({"font-size":"17px","font-weight":"bold","color":c["text"],
                   "margin":"22px 0 10px","padding":"0","line-height":"1.6"})
    elif tag == "h4":
        s.update({"font-size":"16px","font-weight":"bold","color":c["sec"],
                   "margin":"18px 0 8px","line-height":"1.6"})
    elif tag == "p":
        s.update({"font-size":c["font_body"],"color":c["text"],
                   "line-height":c["lh"],"letter-spacing":"0.5px","margin":"0 0 14px 0"})
    elif tag == "blockquote":
        s.update({"font-size":c["font_body"],"color":c["sec"],
                   "line-height":c["lh"],"margin":"18px 0","padding":"12px 18px",
                   "border-left":f"4px solid {c['accent']}","background-color":c["bg"]})
    elif tag == "pre":
        s.update({"font-size":"13px","line-height":"1.6","margin":"16px 0",
                   "padding":"16px 18px","background-color":c["code"],
                   "border-radius":"6px","overflow-x":"auto",
                   "font-family":"Consolas, 'Liberation Mono', Menlo, Courier, monospace"})
    elif tag == "code":
        s.update({"font-size":"13px","padding":"2px 6px","background-color":c["alight"],
                   "border-radius":"3px",
                   "font-family":"Consolas, 'Liberation Mono', Menlo, Courier, monospace",
                   "color":c["accent"]})
    elif tag in ("ul","ol"):
        s.update({"font-size":c["font_body"],"color":c["text"],"line-height":c["lh"],
                   "margin":"8px 0 14px","padding-left":"24px"})
    elif tag == "li":
        s.update({"font-size":c["font_body"],"color":c["text"],"line-height":c["lh"],"margin":"4px 0"})
    elif tag == "a":
        s.update({"color":c["accent"],"text-decoration":"none","border-bottom":f"1px solid {c['accent']}"})
    elif tag == "img":
        s.update({"max-width":"100%","height":"auto","display":"block","margin":"16px auto","border-radius":"4px"})
    elif tag == "hr":
        s.update({"margin":"24px 0","border":"none","border-top":f"1px solid {c['border']}"})
    elif tag == "table":
        s.update({"font-size":"15px","color":c["text"],"line-height":"1.6","margin":"16px 0",
                   "border-collapse":"collapse","width":"100%"})
    elif tag == "th":
        s.update({"padding":"10px 14px","border":f"1px solid {c['border']}",
                   "background-color":c["accent"],"color":"#FFF","font-weight":"bold","text-align":"center"})
    elif tag == "td":
        s.update({"padding":"8px 14px","border":f"1px solid {c['border']}","text-align":"left"})
    elif tag == "strong":
        s.update({"color":c["accent"],"font-weight":"bold"})
    elif tag == "em":
        s.update({"font-style":"italic"})
    elif tag == "s":
        s.update({"text-decoration":"line-through","color":c["sec"]})
    elif tag == "u":
        s.update({"text-decoration":"underline"})
    return style(s)


# ═══════ 内容分析 ═══════

def analyze_content(md_text):
    lines = md_text.split("\n")
    total = len(md_text)
    cb = len(re.findall(r'^```', md_text, re.M)) // 2
    bq = len(re.findall(r'^>', md_text, re.M))
    tl = len(re.findall(r'^\|.+\|$', md_text, re.M))
    text_lower = md_text.lower()

    tech_score = sum(2 for kw in ["代码","函数","api","python","安装","配置","部署",
        "github","命令","教程","步骤","方法","实现","server","client","数据库",
        "vue","react","docker","kubernetes","cli","terminal","npm","git"] if kw in text_lower)
    opinion_score = sum(2 for kw in ["为什么","但我认为","我建议","不值得","别再","警惕",
        "真相","反思","批判","我反对","说实话","千万别"] if kw in text_lower)
    narrative_score = sum(1 for kw in ["记得","小时候","想起","感觉","也许","后来",
        "曾经","回忆","我","我的","我们","那天","那年"] if kw in text_lower)
    narrative_score += sum(3 for kw in ["我见过","我去过","我做过","我经历过","我记得",
        "我小时候","那一年","有一次"] if kw in text_lower)

    tech_score += cb * 8 + tl * 3
    opinion_score += bq * 2

    if cb >= 1 and tech_score >= max(opinion_score, narrative_score):
        return "azure"
    if opinion_score >= 5 and opinion_score > narrative_score:
        return "cinnabar"
    return "ink"


# ═══════ 排版组件（fenced div） ═══════

FENCED_TYPES = ("card", "highlight", "quote", "tip", "section")

def render_component(ctype, content, profile):
    """将 ::: type ... ::: 块渲染为 HTML 组件。"""
    c = C[profile]
    inner_html = _render_inner(content, profile)
    base_font = f"font-size:{c['font_body']};line-height:{c['lh']};color:{c['text']}"

    if ctype == "card":
        return (
            f'<div style="background:#fff;border:1px solid {c["border"]};'
            f'border-radius:8px;padding:16px 18px;margin:18px 0;{base_font}">\n'
            f'{inner_html}\n</div>'
        )
    elif ctype == "highlight":
        return (
            f'<div style="background:{c["alight"]};border-radius:6px;'
            f'padding:14px 18px;margin:18px 0;{base_font}">\n'
            f'{inner_html}\n</div>'
        )
    elif ctype == "quote":
        return (
            f'<div style="background:{c["bg"]};border-left:6px solid {c["accent"]};'
            f'border-radius:0 6px 6px 0;padding:18px 20px;margin:20px 0;'
            f'font-size:18px;line-height:{c["lh"]};color:{c["accent"]};font-weight:bold">\n'
            f'{inner_html}\n</div>'
        )
    elif ctype == "tip":
        return (
            f'<div style="background:{c["bg"]};border-left:4px solid {c["accent"]};'
            f'border-radius:0 6px 6px 0;padding:12px 16px;margin:16px 0;{base_font}">'
            f'<span style="display:inline-block;width:6px;height:6px;'
            f'background:{c["accent"]};border-radius:50%;margin-right:8px;'
            f'vertical-align:middle"></span>{inner_html.strip()}\n</div>'
        )
    elif ctype == "section":
        return (
            f'<div style="text-align:center;margin:28px 0 18px 0">\n'
            f'<span style="display:inline-block;background:{c["accent"]};color:#fff;'
            f'padding:6px 18px;border-radius:20px;font-size:15px;'
            f'font-weight:bold;letter-spacing:2px">{html_escape(content.strip())}</span>\n</div>'
        )
    return inner_html


def _render_inner(md_text, profile):
    """渲染组件内部的 markdown 内容为内联样式 HTML。"""
    md = MarkdownIt("default", {"breaks":True,"html":False,"linkify":False,"typographer":True})
    html = md.render(md_text.strip())
    # 只需要内联标签样式
    c = C[profile]
    html = re.sub(r'<strong>(.*?)</strong>', lambda m: f'<strong style="color:{c["accent"]};font-weight:bold">{m.group(1)}</strong>', html)
    html = re.sub(r'<em>(.*?)</em>', lambda m: f'<em style="font-style:italic">{m.group(1)}</em>', html)
    html = re.sub(r'<a(?![^>]*style=)([^>]*)>', lambda m: f'<a style="color:{c["accent"]};text-decoration:none;border-bottom:1px solid {c["accent"]}" {m.group(1)}>', html)
    html = re.sub(r'<code>(.*?)</code>', lambda m: f'<code style="font-size:13px;padding:2px 6px;background:{c["alight"]};border-radius:3px;font-family:Consolas,monospace;color:{c["accent"]}">{m.group(1)}</code>', html)
    html = re.sub(r'<p>', f'<p style="margin:0 0 10px 0;line-height:{c["lh"]};color:{c["text"]}">', html)
    return html


def parse_fenced_divs(md_text, profile):
    """解析 ::: type ... ::: 围栏块，替换为 HTML 组件。"""
    def _replace(m):
        ctype = m.group(1).strip()
        if ctype not in FENCED_TYPES:
            return m.group(0)
        content = m.group(2).strip()
        return render_component(ctype, content, profile)

    md_text = re.sub(
        r'^:::\s*(\w+)\s*\n(.*?)\n:::\s*$',
        _replace, md_text, flags=re.MULTILINE | re.DOTALL
    )
    return md_text


# ═══════ 语法高亮 ═══════

def format_code(code, lang=""):
    try:
        lexer = get_lexer_by_name(lang, stripall=True) if lang else guess_lexer(code)
    except Exception:
        lexer = None
    if lexer:
        return highlight(code, lexer, HtmlFormatter(nowrap=True, noclasses=True))
    return html_escape(code)


def _process_code_block(m, ts_fn, fmt_fn):
    code = m.group(2)
    code = code.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"')
    highlighted = fmt_fn(code, m.group(1))
    return f'<pre style="{ts_fn("pre")}"><code style="{ts_fn("code")}">{highlighted}</code></pre>'


# ═══════ 主转换 ═══════

def convert(md_text, profile="azure", title=""):
    # 第一步：解析 fenced divs
    md_text = parse_fenced_divs(md_text, profile)

    md = MarkdownIt("default", {"breaks":True,"html":True,"linkify":False,"typographer":True})
    raw_html = md.render(md_text)
    c = C[profile]

    def ts(tag):
        return tag_style(profile, tag)

    # 代码块
    raw_html = re.sub(
        r'<pre><code class="language-(\w*)">(.*?)</code></pre>',
        lambda m: _process_code_block(m, ts, format_code),
        raw_html, flags=re.DOTALL
    )
    raw_html = re.sub(r'<code>(?!\s)(.*?)(?<!\s)</code>',
        lambda m: f'<code style="{ts("code")}">{m.group(1)}</code>', raw_html)

    # 表格
    raw_html = re.sub(r'<table>', f'<table style="{ts("table")}">', raw_html)
    raw_html = re.sub(r'<th(?![^>]*style=)>', f'<th style="{ts("th")}">', raw_html)
    raw_html = re.sub(r'<td(?![^>]*style=)>', f'<td style="{ts("td")}">', raw_html)

    # 自闭合
    raw_html = re.sub(r'<hr>', f'<hr style="{ts("hr")}" />', raw_html)
    raw_html = re.sub(r'<img(?![^>]*style=)([^>]*)>',
        lambda m: f'<img style="{ts("img")}" {m.group(1)}>', raw_html)

    # 标题
    for lv in range(1,7):
        t = f"h{lv}"
        raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>',
            lambda m, tag=t: f'<{tag} style="{ts(tag)}" {m.group(1)}>', raw_html)

    # 块级
    for t in ["p","blockquote","pre"]:
        raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>',
            lambda m, tag=t: f'<{tag} style="{ts(tag)}" {m.group(1)}>', raw_html)

    # 列表
    for t in ["ul","ol"]:
        raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>',
            lambda m, tag=t: f'<{tag} style="{ts(tag)}" {m.group(1)}>', raw_html)
    raw_html = re.sub(r'<li(?![^>]*style=)([^>]*)>',
        lambda m: f'<li style="{ts("li")}" {m.group(1)}>', raw_html)

    # 内联（词边界）
    for pat, tg in [
        (r'<(strong|b)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "strong"),
        (r'<(em|i)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "em"),
        (r'<(s|del)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "s"),
        (r'<u(?![a-zA-Z])(?![^>]*style=)([^>]*)>', "u"),
        (r'<a(?![^>]*style=)([^>]*)>', "a"),
    ]:
        raw_html = re.sub(pat, lambda m, t=tg: f'<{m.group(1) if m.lastindex and m.lastindex>=2 and m.group(2) is not None else tg} style="{ts(t)}" {m.group(m.lastindex)}>', raw_html)

    # 包装
    title_html = f'<h1 style="{ts("h1")}">{html_escape(title)}</h1>\n' if title else ""
    
    # 后处理：把组件后裸露的文本段落包上 <p>
    raw_html = re.sub(r'(?<=</div>)\s*\n(?!\s*<)([^<\n][^\n]*)', lambda m: f'\n<p style="{ts("p")}">{m.group(1).strip()}</p>', raw_html)
    raw_html = re.sub(r'(?<=</span>)\s*\n(?!\s*<)([^<\n][^\n]*)', lambda m: f'\n<p style="{ts("p")}">{m.group(1).strip()}</p>', raw_html)
    
    # 修复 --- 被渲染为文本的问题
    raw_html = re.sub(r'<p[^>]*>---</p>', f'<hr style="{ts("hr")}" />', raw_html)

    output = (
        f'<section style="max-width:677px;margin:0 auto;padding:10px 16px;'
        f'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Hiragino Sans GB\','
        f'\'Microsoft YaHei\',\'Helvetica Neue\',Arial,sans-serif;">\n'
        f'{title_html}{raw_html.strip()}\n</section>'
    )
    return output


# ═══════ 入口 ═══════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Markdown → 微信公众号 HTML")
    parser.add_argument("input", help="Markdown 文件路径")
    parser.add_argument("--style", choices=list(C.keys()), default=None,
                        help="排版风格: ink (温墨) / azure (青蓝) / cinnabar (赤丹)")
    parser.add_argument("output", nargs="?", help="输出 HTML 路径（可选）")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在: {args.input}"); sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        md_text = f.read()

    title = ""
    fm = re.match(r"^---\s*\n(.*?)\n---", md_text, re.DOTALL)
    if fm:
        t = re.search(r"^title:\s*['\"]?(.+?)['\"]?$", fm.group(1), re.M)
        if t: title = t.group(1).strip()
        md_text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", md_text, flags=re.DOTALL, count=1)

    chosen = args.style or analyze_content(md_text)
    output_html = convert(md_text, profile=chosen, title=title)

    out_path = args.output or re.sub(r'\.\w+$', '', args.input) + ".wechat.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_html)

    p = C[chosen]
    print(f"✅ 已生成: {out_path}")
    print(f"   风格: {p['emoji']} / {chosen} — {len(output_html)} 字符")
    print(f"   用法: 浏览器打开 → 全选复制 → 粘贴到微信编辑器")


if __name__ == "__main__":
    main()
