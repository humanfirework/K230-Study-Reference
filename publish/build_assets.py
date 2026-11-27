# -*- coding: utf-8 -*-
"""在 CI 里生成 release 附件：真题索引、真题 zip、2025 工程 zip，外加已生成的打印清单。"""
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "out"
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / "NUEDC_TOPIC-master" / "真题"
pdfs = sorted(p.relative_to(SRC).as_posix() for p in SRC.rglob("*.pdf"))
if len(pdfs) < 100:
    raise SystemExit(f"真题数量异常：{len(pdfs)}")

# 1) 索引
lines = [
    "# 真题清单（1994–2026）",
    "",
    f"> 共 **{len(pdfs)}** 个 PDF，按年份排列。路径相对 `真题/`。",
    "> 题目版权归命题方；本清单只做索引，文件来自 `NUEDC_TOPIC-master`（左岚整理）。",
    "",
    "| 年份 | 文件 |",
    "| --- | --- |",
]
lines += [f"| {rel.split('/')[0]} | `{rel}` |" for rel in pdfs]
lines += [
    "",
    "## 另有两类，不在本索引里",
    "",
    "- `综合测评/`：12 个 PDF（2011–2025 奇数年），含 Multisim / Matlab 模型。",
    "- `参考资料/`：2 个 PDF（TI 手册），约 20 MB。",
    "",
    "完整仓库：<https://github.com/humanfirework/K230-Study-Reference>",
]
(OUT / "nuedc_paper_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# 2) 真题 zip
note = OUT / "_source.md"
note.write_text(
    "# 真题包说明\n\n"
    "- 来源：`NUEDC_TOPIC-master`（左岚整理的电赛真题档案）。\n"
    f"- 内容：1994–2026 年真题 PDF 共 {len(pdfs)} 份；综合测评 12 份、参考资料 2 份不在本包内。\n"
    "- 版权：题目版权归全国大学生电子设计竞赛组委会及命题方，这里只做备赛查阅，不得用于商业用途。\n"
    "- 仓库：https://github.com/humanfirework/K230-Study-Reference\n",
    encoding="utf-8",
)
with zipfile.ZipFile(OUT / "nuedc_papers_1994-2026.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    z.write(note, "真题/_来源与使用.md")
    for rel in pdfs:
        z.write(SRC / rel, "真题/" + rel)
note.unlink()

# 3) 2025 工程 zip
base = ROOT / "07_contest" / "2025_E_self_aiming"
with zipfile.ZipFile(OUT / "2025_E_self_aiming.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name in ["README.md", "E题_简易自行瞄准装置.pdf"]:
        z.write(base / name, "2025_E_self_aiming/" + name)
    for sub in ["result", "find_rect", "methods_reference"]:
        for p in sorted((base / sub).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                z.write(p, "2025_E_self_aiming/" + p.relative_to(base).as_posix())

# 4) 打印清单（预生成，随仓库提交）
shutil.copyfile(ROOT / "docs" / "assets" / "checklist_A4.pdf", OUT / "checklist_A4.pdf")

for p in sorted(OUT.iterdir()):
    print(f"{p.name}: {p.stat().st_size / 1024 / 1024:.1f} MB")
