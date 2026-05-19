#!/usr/bin/env python3
"""
Markdown → 微信公众号 HTML 转换引擎 (丰富排版组件版)

支持排版组件:
  卡片: card.highlight, card.white, card.quote, card.tip, card.banner, card.ribbon
  标题装饰: [装饰线], [左框], [圆标], [下划线], [色带]
  分割线变体: ===, ***, ~~~, ...
  内联装饰: ==高亮==, !!强调!!, ((标签))

用法:
  python3 wechat-format.py input.md [output.html] [--style ink|azure|cinnabar]
"""

import sys, os, re
from markdown_it import MarkdownIt
from pygments import highlight as pyg_highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from html import escape as html_escape

# ═══════════════════ 色彩配置 ═══════════════════

C = {
    "ink": {
        "accent":"#8B6914","alight":"#FDF6EC","text":"#3D3D3D","sec":"#7A7A7A",
        "border":"#E8E0D0","bg":"#FAF8F5","code":"#F5F3EF",
        "font_body":"17px","font_h1":"24px","font_h2":"20px","lh":"1.85",
        "emoji":"\U0001f4dd",
    },
    "azure": {
        "accent":"#2B6CB0","alight":"#EBF4FF","text":"#333333","sec":"#666666",
        "border":"#E8E8E8","bg":"#F7F8FA","code":"#F5F6F7",
        "font_body":"16px","font_h1":"22px","font_h2":"19px","lh":"1.75",
        "emoji":"\U0001f537",
    },
    "cinnabar": {
        "accent":"#C0392B","alight":"#FDF0EF","text":"#2D2D2D","sec":"#6B6B6B",
        "border":"#E0D0D0","bg":"#F9F5F4","code":"#F4F0EF",
        "font_body":"17px","font_h1":"24px","font_h2":"20px","lh":"1.8",
        "emoji":"\U0001f525",
    },
}

# ═══════════════════ 卡片组件 ═══════════════════

CARD_CONFIGS = {
    "highlight": {
        "bg": lambda c: c["alight"], "border": "none", "radius": "12px",
        "pad": "20px 24px", "text_color": lambda c: c["text"],
    },
    "white": {
        "bg": "#FFFFFF", "border": lambda c: f"1px solid {c['border']}", "radius": "12px",
        "pad": "20px 24px", "text_color": lambda c: c["text"],
    },
    "quote": {
        "bg": lambda c: c["bg"], "border": lambda c: f"4px solid {c['accent']}",
        "radius": "0 12px 12px 0", "pad": "18px 24px",
        "text_color": lambda c: c["accent"], "font_weight": "bold",
        "font_size": "19px",
    },
    "tip": {
        "bg": lambda c: c["bg"], "border": lambda c: f"4px solid {c['accent']}",
        "radius": "0 12px 12px 0", "pad": "16px 20px",
        "text_color": lambda c: c["text"],
    },
    "banner": {
        "bg": lambda c: c["accent"], "border": "none", "radius": "8px",
        "pad": "28px 24px", "text_color": "#FFFFFF", "text_align": "center",
        "font_size": "20px",
    },
    "ribbon": {
        "bg": lambda c: c["alight"], "border": "none", "radius": "0",
        "pad": "14px 24px", "text_color": lambda c: c["accent"],
        "text_align": "center", "font_weight": "bold", "font_size": "16px",
    },
}

def _resolve(v, c):
    return v(c) if callable(v) else v

def render_card(variant, content, profile):
    c = C[profile]
    cfg = CARD_CONFIGS.get(variant, CARD_CONFIGS["white"])

    bg = _resolve(cfg["bg"], c)
    border = _resolve(cfg["border"], c)
    pad = cfg["pad"]
    tc = _resolve(cfg["text_color"], c)
    ta = cfg.get("text_align", "left")
    fw = cfg.get("font_weight", "normal")
    fs = cfg.get("font_size", c["font_body"])

    # Container style
    if variant == "quote":
        container = (
            f"background:{bg};border-left:{border};border-radius:{cfg['radius']};"
            f"padding:{pad};margin:16px 0;text-align:{ta};line-height:{c['lh']};"
        )
    else:
        container = (
            f"background:{bg};border:{border};border-radius:{cfg['radius']};"
            f"padding:{pad};margin:16px 0;text-align:{ta};line-height:{c['lh']};"
        )

    # Split content into paragraphs
    paras = [p.strip() for p in content.strip().split('\n\n') if p.strip()]
    inner = ""
    if variant == "tip":
        inner += f'<p style="margin:0 0 8px 0;font-size:14px;color:{c["accent"]};font-weight:bold;">💡 提示</p>'
    for i, para in enumerate(paras):
        last = (i == len(paras) - 1) and variant != "tip"
        mb = "0" if last else "0 0 10px 0"
        bc = tc if variant == "banner" else None
        ph = _inline_md(para, profile, bold_color=bc)
        inner += f'<p style="margin:{mb};line-height:{c["lh"]};color:{tc};font-size:{fs};font-weight:{fw};">{ph}</p>'

    return f'<section style="{container}">{inner}</section>'

def _inline_md(text, profile, bold_color=None):
    """Process inline markdown + custom markers within card content."""
    c = C[profile]
    if bold_color is None:
        bold_color = c["accent"]
    text = re.sub(
        r'==([^=]+?)==',
        r'<span style="background:#FFF3CD;padding:2px 6px;border-radius:3px;color:#856404;">\1</span>',
        text
    )
    # Custom: !!emphasis!!
    text = re.sub(
        r'!!([^!]+?)!!',
        rf'<span style="color:{c["accent"]};font-weight:bold;padding:0 2px;">\1</span>',
        text
    )
    # Custom: ((label))
    text = re.sub(
        r'\(\(([^)]+?)\)\)',
        rf'<span style="display:inline-block;border:1px solid {c["accent"]}50;color:{c["accent"]};font-size:12px;padding:1px 8px;border-radius:3px;margin:0 2px;white-space:nowrap;">\1</span>',
        text
    )
    # Standard inline markdown
    text = re.sub(
        r'\*\*(.+?)\*\*',
        rf'<strong style="color:{bold_color};font-weight:bold;">\1</strong>',
        text
    )
    text = re.sub(r'\*(.+?)\*', r'<em style="font-style:italic;">\1</em>', text)
    text = re.sub(
        r'`(.+?)`',
        lambda m: (
            f'<code style="display:inline-block;background:{c["alight"]};color:{c["accent"]};'
            f'font-size:13px;padding:2px 8px;border-radius:4px;font-family:Consolas,monospace;">{m.group(1)}</code>'
        ),
        text
    )
    text = re.sub(
        r'\[(.+?)\]\((.+?)\)',
        rf'<a style="color:{c["accent"]};text-decoration:none;border-bottom:1px solid {c["accent"]};">\1</a>',
        text
    )
    return text

# ═══════════════════ 标题装饰 ═══════════════════

TITLE_DECORATORS = ("装饰线", "左框", "圆标", "下划线", "色带")
_TITLE_RE = re.compile(
    r'^(#{1,6})\s*\[' + '(' + '|'.join(TITLE_DECORATORS) + r')\]\s+(.+)$',
    re.MULTILINE
)

def render_decorated_title(match, profile):
    level = len(match.group(1))
    decorator = match.group(2)
    text = match.group(3).strip()
    c = C[profile]
    fs_map = {1: "24px", 2: "21px", 3: "19px", 4: "17px"}
    fs = fs_map.get(level, "17px")
    ac = c["accent"]

    if decorator == "装饰线":
        return (
            f'<section style="display:flex;align-items:center;justify-content:center;margin:32px 0 16px 0;">'
            f'<span style="flex:1;height:1px;background:{ac}50;"></span>'
            f'<span style="padding:0 16px;font-size:{fs};font-weight:bold;color:{ac};letter-spacing:2px;white-space:nowrap;">{text}</span>'
            f'<span style="flex:1;height:1px;background:{ac}50;"></span>'
            f'</section>'
        )
    elif decorator == "左框":
        return (
            f'<section style="margin:28px 0 14px 0;padding:10px 0 10px 16px;border-left:4px solid {ac};">'
            f'<span style="font-size:{fs};font-weight:bold;color:{ac};letter-spacing:1px;">{text}</span>'
            f'</section>'
        )
    elif decorator == "圆标":
        m = re.match(r'(\d+|[一二三四五六七八九十])[.、．\s]*(.*)', text)
        num, rest = (m.group(1), m.group(2)) if m else ("◆", text)
        return (
            f'<section style="display:flex;align-items:center;gap:12px;margin:28px 0 14px 0;">'
            f'<span style="display:inline-flex;width:32px;height:32px;background:{ac};color:#FFF;'
            f'font-size:16px;font-weight:bold;border-radius:50%;align-items:center;justify-content:center;flex-shrink:0;">{num}</span>'
            f'<span style="font-size:{fs};font-weight:bold;color:{ac};letter-spacing:1px;">{rest}</span>'
            f'</section>'
        )
    elif decorator == "下划线":
        return (
            f'<section style="text-align:center;margin:32px 0 16px 0;">'
            f'<span style="display:inline-block;font-size:{fs};font-weight:bold;color:{ac};'
            f'padding-bottom:8px;border-bottom:3px solid {ac}60;letter-spacing:2px;">{text}</span>'
            f'</section>'
        )
    elif decorator == "色带":
        return (
            f'<section style="margin:28px 0 14px 0;padding:12px 18px;background:{c["alight"]};'
            f'border-left:3px solid {ac};">'
            f'<span style="font-size:{fs};font-weight:bold;color:{ac};letter-spacing:1px;">{text}</span>'
            f'</section>'
        )
    return ""  # fallback

# ═══════════════════ 分割线变体 ═══════════════════

DIVIDER_FNS = {
    "===": lambda c: (f'<section style="margin:24px 0;text-align:center;">'
                      f'<span style="display:inline-block;width:60%;height:0;'
                      f'border-top:2px dashed {c["accent"]}40;"></span></section>'),
    "***": lambda c: (f'<section style="margin:24px 0;text-align:center;'
                      f'letter-spacing:8px;color:{c["accent"]}60;font-size:16px;">✦ ✦ ✦</section>'),
    "~~~": lambda c: (f'<section style="margin:24px 0;text-align:center;'
                      f'letter-spacing:4px;color:{c["accent"]}40;font-size:18px;">~ ~ ~</section>'),
    "...": lambda c: (f'<section style="margin:24px 0;text-align:center;">'
                      f'<span style="display:inline-block;width:40px;height:4px;'
                      f'border-radius:2px;background:{c["accent"]}60;"></span></section>'),
}

# ═══════════════════ 语法高亮 ═══════════════════

def _format_code(code, lang=""):
    try:
        lexer = get_lexer_by_name(lang, stripall=True) if lang else guess_lexer(code)
        return pyg_highlight(code, lexer, HtmlFormatter(nowrap=True, noclasses=True))
    except Exception:
        return html_escape(code)

def _unescape(text):
    return text.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"')

# ═══════════════════ 主转换 ═══════════════════

def tag_style(tag, c):
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
                   "margin":"22px 0 10px","line-height":"1.6"})
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
                   "border-radius":"6px","overflow-x":"auto"})
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
    if not s:
        return ""
    return "; ".join(f"{k}:{v}" for k,v in s.items())


def convert(md_text, profile="azure", title=""):
    c = C[profile]
    sentinels = {}
    counter = [0]
    SENT = "<!--WECHAT_CMP_"

    # ── Phase 1: Card blocks ──
    def _replace_card(m):
        variant_str = m.group(1).strip()
        content = m.group(3).strip()
        if "." in variant_str:
            parts = variant_str.split(".")
            if parts[0] == "card" and parts[1] in CARD_CONFIGS:
                card_variant = parts[1]
            else:
                return m.group(0)
        elif variant_str in CARD_CONFIGS:
            card_variant = variant_str
        elif variant_str == "card":
            card_variant = "white"  # default card
        else:
            return m.group(0)
        sid = f"{SENT}{counter[0]}_CARD-->"
        counter[0] += 1
        sentinels[sid] = render_card(card_variant, content, profile)
        return sid

    md_text = re.sub(
        r'^::: ?([\w.]+) ?(:::)? *\n(.*?)\n:::\s*$',
        _replace_card, md_text, flags=re.MULTILINE | re.DOTALL
    )

    # ── Phase 2: Decorated titles ──
    def _replace_title(m):
        sid = f"{SENT}{counter[0]}_TITLE-->"
        counter[0] += 1
        sentinels[sid] = render_decorated_title(m, profile)
        return sid
    md_text = _TITLE_RE.sub(_replace_title, md_text)

    # ── Phase 3: Divider variants ──
    for dv in DIVIDER_FNS:
        def _make_div_replacer(div):
            def _replace(m):
                sid = f"{SENT}{counter[0]}_DIV-->"
                counter[0] += 1
                sentinels[sid] = DIVIDER_FNS[div](c)
                return sid
            return _replace
        md_text = re.sub(
            rf'^{re.escape(dv)}\s*$',
            _make_div_replacer(dv), md_text, flags=re.MULTILINE
        )

    # ── Phase 4: MarkdownIt render ──
    md = MarkdownIt("default", {"breaks":True, "html":True, "linkify":False, "typographer":True})
    raw_html = md.render(md_text)

    # ── Phase 5: Inline markers on text nodes ──
    def _apply_inline(html):
        parts = re.split(r'(<[^>]*>)', html)
        for i, part in enumerate(parts):
            if not part.startswith('<'):
                part = re.sub(
                    r'==([^=]+?)==',
                    r'<span style="background:#FFF3CD;padding:2px 6px;border-radius:3px;color:#856404;">\1</span>',
                    part
                )
                part = re.sub(
                    r'!!([^!]+?)!!',
                    rf'<span style="color:{c["accent"]};font-weight:bold;padding:0 2px;">\1</span>',
                    part
                )
                part = re.sub(
                    r'\(\(([^)]+?)\)\)',
                    rf'<span style="display:inline-block;border:1px solid {c["accent"]}50;color:{c["accent"]};font-size:12px;padding:1px 8px;border-radius:3px;margin:0 2px;white-space:nowrap;">\1</span>',
                    part
                )
                parts[i] = part
        return ''.join(parts)
    raw_html = _apply_inline(raw_html)

    # ── Phase 6: Style application ──
    def ts(tag):
        return tag_style(tag, c)

    # Headings
    for lv in range(1, 7):
        t = f"h{lv}"
        s = ts(t)
        if s:
            raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>', f'<{t} style="{s}" \\1>', raw_html)

    # Block elements
    for t in ["p", "blockquote", "pre"]:
        s = ts(t)
        if s:
            raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>', f'<{t} style="{s}" \\1>', raw_html)

    # Lists
    for t in ["ul", "ol"]:
        s = ts(t)
        if s:
            raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>', f'<{t} style="{s}" \\1>', raw_html)
    li_s = ts("li")
    if li_s:
        raw_html = re.sub(r'<li(?![^>]*style=)([^>]*)>', f'<li style="{li_s}" \\1>', raw_html)

    # Inline
    strong_s = ts("strong")
    if strong_s:
        raw_html = re.sub(r'<(strong|b)(?![a-zA-Z])(?![^>]*style=)([^>]*)>', f'<strong style="{strong_s}" \\2>', raw_html)
    a_s = ts("a")
    if a_s:
        raw_html = re.sub(r'<a(?![^>]*style=)([^>]*)>', f'<a style="{a_s}" \\1>', raw_html)

    # Tables
    for t, style_key in [("table", "table"), ("th", "th"), ("td", "td")]:
        s = ts(style_key)
        if s:
            raw_html = re.sub(f'<{t}(?![^>]*style=)([^>]*)>', f'<{t} style="{s}" \\1>', raw_html)

    # hr
    hr_s = ts("hr")
    if hr_s:
        raw_html = re.sub(r'<hr>', f'<hr style="{hr_s}" />', raw_html)
    img_s = ts("img")
    if img_s:
        raw_html = re.sub(r'<img(?![^>]*style=)([^>]*)>', f'<img style="{img_s}" \\1>', raw_html)

    # Code: blocks with Pygments
    raw_html = re.sub(
        r'<pre><code class="language-(\w*)">(.*?)</code></pre>',
        lambda m: (f'<pre style="{ts("pre")}"><code style="{ts("code")}">'
                   f'{_format_code(_unescape(m.group(2)), m.group(1))}'
                   f'</code></pre>'),
        raw_html, flags=re.DOTALL
    )

    # Inline code → pill style for short code
    raw_html = re.sub(
        r'<code>(?!\s)(.{1,10}?)(?<!\s)</code>',
        lambda m: (f'<code style="display:inline-block;background:{c["alight"]};color:{c["accent"]};'
                   f'font-size:13px;padding:2px 8px;border-radius:4px;font-family:Consolas,monospace;">{m.group(1)}</code>'),
        raw_html
    )

    # ── Phase 7: Replace sentinels ──
    for sid, rendered in sentinels.items():
        raw_html = raw_html.replace(sid, rendered)

    # ── Phase 8: Post-processing ──
    raw_html = re.sub(r'<p[^>]*>---\s*</p>', f'<hr style="{ts("hr")}" />', raw_html)

    # Build output
    title_html = f'<h1 style="{ts("h1")}">{html_escape(title)}</h1>\n' if title else ""
    output = (
        f'<section style="max-width:677px;margin:0 auto;padding:10px 16px;'
        f'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Hiragino Sans GB\','
        f'\'Microsoft YaHei\',\'Helvetica Neue\',Arial,sans-serif;">\n'
        f'{title_html}{raw_html.strip()}\n</section>'
    )
    return output


# ═══════════════════ 内容分析 ═══════════════════

def analyze_content(md_text):
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


# ═══════════════════ 入口 ═══════════════════

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

    # Extract title from frontmatter
    title = ""
    fm = re.match(r"^---\s*\n(.*?)\n---", md_text, re.DOTALL)
    if fm:
        t = re.search(r"^title:\s*['\"]?(.+?)['\"]?$", fm.group(1), re.M)
        if t:
            title = t.group(1).strip()
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
