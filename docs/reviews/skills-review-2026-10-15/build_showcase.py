"""Build a local, self-contained viewer for the retained-result dialogue pairs."""

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = {
    "career": "事业与岗位",
    "relationship": "双方相处",
    "timing": "阶段与时运",
    "health": "健康文化",
    "learning": "学习与性格",
    "natal": "西占本命",
    "divination": "梅花问事",
    "profile": "三体系画像",
    "space": "空间与物件",
}


def inline(text):
    text = html.escape(text)
    text = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def render(text):
    """Render only the small Markdown subset used in these saved answers."""
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    tag = "th" if not rows else "td"
                    rows.append(
                        "<tr>"
                        + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
                        + "</tr>"
                    )
                i += 1
            blocks.append(
                '<div class="table-wrap"><table>' + "".join(rows) + "</table></div>"
            )
            continue
        if line.startswith("#"):
            blocks.append("<h3>" + inline(line.lstrip("# ")) + "</h3>")
        else:
            paragraph = [line]
            while (
                i + 1 < len(lines)
                and lines[i + 1].strip()
                and not lines[i + 1].lstrip().startswith(("|", "#"))
            ):
                i += 1
                paragraph.append(lines[i])
            blocks.append("<p>" + "<br>".join(inline(s) for s in paragraph) + "</p>")
        i += 1
    return "".join(blocks)


def main():
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    buttons, sections = [], []
    for i, case in enumerate(cases):
        case_id = case["id"]
        label = LABELS[case_id]
        buttons.append(
            f'<button role="tab" id="tab-{case_id}" aria-controls="case-{case_id}" aria-selected="{str(i == 0).lower()}" data-case="{case_id}">{label}</button>'
        )
        answers = {}
        for variant in ("baseline", "revised"):
            path = HERE / "dialogues" / variant / f"{case_id}.md"
            answers[variant] = render(path.read_text())
        sources = " · ".join(
            f'<a href="{html.escape(path)}">{html.escape(Path(path).stem)}</a>'
            for path in case["evidence"]
        )
        sections.append(
            f'<section role="tabpanel" aria-labelledby="tab-{case_id}" id="case-{case_id}" {"" if i == 0 else "hidden"}>'
            f'<div class="question"><span>用户问题 · 虚构资料</span><p>{inline(case["prompt"])}</p></div>'
            f'<div class="pair"><article class="old"><h2>基线技能</h2>{answers["baseline"]}</article>'
            f"<article><h2>修订技能</h2>{answers['revised']}</article></div>"
            f"<footer>保留的同一批实际计算：{sources}</footer></section>"
        )
    page = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>FateBridge · 九个场景的实际解释</title>
<style>
:root{color-scheme:light;--ink:#203633;--muted:#62716b;--line:#dbe3db;--accent:#216751}
*{box-sizing:border-box}body{margin:0;background:#f6f7f2;color:var(--ink);font:16px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
header,main{max-width:1320px;margin:auto;padding:30px 38px}header{padding-bottom:18px}header small{color:var(--accent);font-weight:650;letter-spacing:.12em}
h1{font-size:32px;line-height:1.35;letter-spacing:-.03em;margin:10px 0 16px}header p{max-width:900px;color:var(--muted);margin:8px 0}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}button{font:inherit;cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:24px;padding:7px 17px}button[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:white}button:focus-visible,a:focus-visible{outline:3px solid #d68e4c;outline-offset:3px}
.controls{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px;color:var(--muted);font-size:14px}.controls label{cursor:pointer}input{accent-color:var(--accent)}
.question{border-left:3px solid #9ab29c;padding:12px 22px;background:#edf1e8;border-radius:0 10px 10px 0;margin:0 0 24px}.question span{font-size:13px;font-weight:650;color:var(--accent)}.question p{margin:5px 0;font-size:15px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:25px 29px;border:1px solid var(--line);border-radius:14px;background:white;min-width:0}article h2{font-size:14px;letter-spacing:.05em;color:var(--accent);margin:0 0 22px}article.old h2{color:var(--muted)}article h3{font-size:19px;margin:24px 0 10px}article p{margin:0 0 17px;overflow-wrap:anywhere}article p:last-child{margin-bottom:0}
body.single .old{display:none}body.single .pair{grid-template-columns:1fr;max-width:920px;margin:auto}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.65}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f0f4ed}.table-wrap{overflow-x:auto;margin-bottom:20px}a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}code{font-size:.9em;background:#f0f3ee;padding:1px 4px;border-radius:3px}footer{font-size:13px;color:var(--muted);padding:20px 0}section[hidden]{display:none}
@media(max-width:850px){header,main{padding:22px 18px}.pair{grid-template-columns:1fr}h1{font-size:26px}article{padding:22px}.controls{align-items:flex-start;flex-direction:column}}
</style><body class="single"><header><small>FATEBRIDGE / SKILLS REVIEW</small>
<h1>让计算中的区别，进入用户的回答</h1>
<p>9 个场景，18 份原始解释。同一批虚构输入与保留结果，由两个独立上下文分别读取基线、修订技能后作答；解释阶段没有重新计算。</p>
<p>这是单次样例评阅，提示词较具体；不代表自动触发率、完整对话体验或预测有效性。修订样例采用领域改进后的冻结版，随后发现的入口语义问题另见审查报告。</p></header><main>
<nav role="tablist" aria-label="咨询场景">BUTTONS</nav>
<div class="controls"><label><input id="compare" type="checkbox"> 同时查看基线，比较具体差异</label><a href="review.md">逐项审查与验证记录</a></div>
SECTIONS</main><script>
const tabs=Array.from(document.querySelectorAll('[role=tab]'));
function select(tab){tabs.forEach(t=>{const active=t===tab;t.setAttribute('aria-selected',String(active));document.getElementById('case-'+t.dataset.case).hidden=!active});}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>select(tab));tab.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;if(next!==undefined){event.preventDefault();tabs[next].focus();select(tabs[next])}})});
document.getElementById('compare').addEventListener('change',event=>document.body.classList.toggle('single',!event.target.checked));
</script></body></html>"""
    (HERE / "showcase.html").write_text(
        page.replace("BUTTONS", "".join(buttons)).replace("SECTIONS", "".join(sections))
    )
    print("Built nine-scene showcase.html")


if __name__ == "__main__":
    main()
