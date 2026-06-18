# FateBridge · Skills（泛心理陪伴套件）

把 FateBridge 引擎的 60+ 命理/占术/占星能力，按**用户真实困扰**重组成一套场景 Skill。  
设计就一句话：**计算交给 FateBridge 引擎算得准，解读交给 Onda 河狸讲得像个人。**

- 引擎完全离线，干支/排盘/合婚分全部由 `python3 -m fatebridge.cli` 算，杜绝 AI 手算幻觉——这是「预测准确」的根。
- 解读遵循 [人味儿写作](https://github.com/orange2ai/renwei-writing)：白描优先、不写金句、保留语气词、禁排比/「不是X而是Y」/万能展望结尾，凶象一律翻译成能过的日子。

---

## 按场景找入口（不用懂术数，带着问题来）

| 你想问的 | 用这个 Skill | 背后调的能力 |
|---------|-------------|-------------|
| 感情、姻缘、桃花、合不合、正缘何时到 | [`onda-yuanfen`](./onda-yuanfen/SKILL.md) | 八字婚姻/正缘桃花、双人合婚、紫微夫妻宫、关系星盘 |
| 事业、财运、跳槽、创业、合伙 | [`onda-shiye`](./onda-shiye/SKILL.md) | 八字事业/财运、合作配合度、时运 |
| 健康倾向、身心节奏、调理方向 | [`onda-jiankang`](./onda-jiankang/SKILL.md) | 八字健康、时运（只谈倾向，不诊断） |
| 今年运势、大运流年、人生转折、择时 | [`onda-shiyun`](./onda-shiyun/SKILL.md) | 时运全系、节气农历、西占推运全套 |
| 卡在一个决定、要不要做某事、求一卦 | [`onda-zhanbu`](./onda-zhanbu/SKILL.md) | 梅花/六爻/奇门/六壬/金口/太乙/宿占/三式 |
| 我是谁、性格天赋、学业、家人、孩子 | [`onda-mingge`](./onda-mingge/SKILL.md) | 八字性格/学业/子女/六亲、命盘综合、紫微 |
| 占星、出生盘、合盘、各流派星盘 | [`onda-xingpan`](./onda-xingpan/SKILL.md) | 标准/希腊/果老/印度/13星座盘、关系盘 |

> 60+ 工具全部在这 7 个场景里有归属；完整工具地图见 [`_shared/fatebridge-engine.md`](./_shared/fatebridge-engine.md)。

---

## 目录结构

```
skills/
├── _shared/
│   ├── fatebridge-engine.md   计算层：CLI 调用、全量工具地图、字段字典、怎么读 snapshot
│   └── onda-counsel.md        解读层：Onda 声音、人味儿规则、凶象翻译、红线、收尾自检
├── onda-yuanfen/              缘分 · 感情合婚
├── onda-shiye/                事业 · 财运
├── onda-jiankang/             健康 · 身心
├── onda-shiyun/               人生时运 · 择时
├── onda-zhanbu/               抉择 · 问事占卜
├── onda-mingge/               认识自己 · 性格天赋
└── onda-xingpan/              星盘 · 占星自观
```

每个场景 Skill 的 `SKILL.md` 都很薄：负责「问什么、调哪个工具、怎么共情」，计算与声音两层共用 `_shared/`。

---

## 给开发者

新增/调整能力时守这条分工：**新维度＝指向对应的 `bazi_*` / 工具目录条目，不要在 Skill 里手写排盘步骤。**

- 引擎侧加工具的方法见仓库 `fatebridge/services/tool_catalog.py`（中央目录，一处声明自动挂到 REST/MCP/CLI）。
- 任何在 Skill 里引用的 CLI 命令，**提交前都要真跑一遍**（引擎离线，无需起服务）：
  ```bash
  python3 -m fatebridge.cli list
  python3 -m fatebridge.cli describe <tool>
  ```

---

## 边界声明

所有解读为传统术数与占星的文化参考视角，不是决定论，不替代医疗、心理、法律、财务等专业意见。幸福靠真实地生活和经营，不靠命定。
