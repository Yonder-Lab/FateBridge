# FateBridge · Skills（泛心理陪伴套件）

FateBridge 引擎里有 80 多个命理、占术和占星工具。这个目录把它们按用户真正会问的出口重新组织成一套场景 Skill。

我们的设计很简单：**计算交给 FateBridge 引擎，解读交给 Onda 河狸。** 引擎离线跑排盘，Onda 负责把结果讲得像个人。

- 所有计算都在本地完成。干支、排盘、合婚分数这些，全部走 `python3 -m fatebridge.cli`，不交给 AI 手算——这样能复核计算过程；计算一致不等于现实预测已验证。
- 解读遵循 [人味儿写作](https://github.com/orange2ai/renwei-writing)：白描优先，不写金句，保留语气词，不排比、不用「不是 X 而是 Y」、不来万能展望式结尾。凶象也要翻译成能过的日子。

---

## 按场景找入口

不用先学术数，带着你的问题直接进：

- **感情、姻缘、桃花、合不合、正缘何时到** → [`onda-yuanfen`](./onda-yuanfen/SKILL.md)  
  调八字婚姻/正缘桃花、双人合婚、紫微夫妻宫、关系星盘。
- **事业、财运、跳槽、创业、合伙** → [`onda-shiye`](./onda-shiye/SKILL.md)  
  调八字事业/财运、合作配合度、时运。
- **健康倾向、身心节奏、调理方向** → [`onda-jiankang`](./onda-jiankang/SKILL.md)  
  调八字健康、时运。只谈倾向，不诊断。
- **今年运势、大运流年、人生转折、择时** → [`onda-shiyun`](./onda-shiyun/SKILL.md)  
  调时运全系、节气农历、西占推运全套。
- **卡在一个决定、要不要做某事、求一卦** → [`onda-zhanbu`](./onda-zhanbu/SKILL.md)  
  调梅花/六爻/奇门/六壬/金口/太乙/宿占/三式。
- **我是谁、性格天赋、学业、家人、孩子** → [`onda-mingge`](./onda-mingge/SKILL.md)  
  调八字性格/学业/子女/六亲、命盘综合、紫微。
- **占星、出生盘、合盘、各流派星盘** → [`onda-xingpan`](./onda-xingpan/SKILL.md)  
  调标准/希腊/果老/印度/13 扇区盘、关系盘。
- **我是一个什么样的人、全面自我分析** → [`onda-zige`](./onda-zige/SKILL.md)  
  八字+紫微+西占三套交叉印证，按主证、旁证与用户需求组织结果，避免重复调用。

80 个工具都落在这 8 个场景里。完整工具地图见 [`_shared/fatebridge-engine.md`](./_shared/fatebridge-engine.md)。

---

## 目录结构

```
skills/
├── _shared/
│   ├── fatebridge-engine.md   计算层：CLI 调用、全量工具地图、字段字典、怎么读 snapshot
│   └── onda-counsel.md        解读层：Onda 声音、人味儿规则、凶象翻译、红线、收尾自检
├── onda-yuanfen/              缘分 · 感情合婚
│   ├── SKILL.md               给人读：问什么、调哪个工具、怎么共情
│   └── agents/interface.yaml  给机器读：场景、工具清单、必填输入、输出契约
├── onda-shiye/                事业 · 财运
├── onda-jiankang/             健康 · 身心
├── onda-shiyun/               人生时运 · 择时
├── onda-zhanbu/               抉择 · 问事占卜
├── onda-mingge/               认识自己 · 性格天赋
├── onda-xingpan/              星盘 · 占星自观
└── onda-zige/                 全面自我画像 · 三套交叉印证
                               （每个 onda-* 都含 SKILL.md + agents/interface.yaml）
```

每个场景 Skill 有两份契约。`SKILL.md` 给人读，薄一点，讲清楚「问什么、调哪个工具、怎么共情」。`agents/interface.yaml` 给 agent 运行时读，机器能直接发现场景触发词、要调的引擎工具、必填出生字段和输出契约。计算和声音两层共用 `_shared/`。

这两份描述都被 `tests/test_skills_interface_contract.py` 锁到引擎 catalog 和 SKILL.md 上。任一方对不上，CI 就挂。

---

## 给开发者

新增或调整能力时，记住这条：**新维度请指向对应的 `bazi_*` 或工具目录条目，不要在 Skill 里手写排盘步骤。**

引擎侧加工具的方法看仓库 `src/fatebridge/services/tool_catalog.py`。它是中央目录，声明一次就会自动挂到 REST、MCP 和 CLI 上。

任何在 Skill 里引用的 CLI 命令，提交前都要真跑一遍。先在虚拟环境安装本仓库（`python -m pip install -e ".[dev]"`，见 [开发指南](../docs/development-guide.md)）。运行 CLI 不用起 REST 服务；`python3` 必须指向已安装包的解释器：

```bash
python3 -m fatebridge.cli list
python3 -m fatebridge.cli describe <tool>
```

如果改了某个 skill 的工具或输入，记得同步更新它的 `agents/interface.yaml`。`engine_tools` 必须与 SKILL.md 里反引号引用的工具完全一致，否则 `tests/test_skills_interface_contract.py` 会失败。

---

## 许可与发布

本套件随 FateBridge 仓库以 **Apache License 2.0** 发布（见仓库根 `LICENSE`）。每个 `agents/interface.yaml` 里标注的 `license` 和 `version` 都与项目一致，并由契约测试校验，保证对外分发时声明和实际不跑偏。

---

## 边界声明

所有解读都是传统术数与占星的文化参考视角，不是决定论，也不替代医疗、心理、法律、财务等专业意见。幸福靠真实地生活和经营，不靠命定。
