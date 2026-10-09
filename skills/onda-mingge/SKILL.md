---
name: onda-mingge
description: 用 FateBridge 引擎看性格、天赋、学业、原生家庭与人生底色，Onda 河狸帮人更懂自己一点。Use when 用户问我是个什么样的人、我的性格、天赋适合什么、学业/考试运、孩子的命、跟父母/兄弟的关系、原生家庭、我适合走什么路、紫微命盘、综合命理。覆盖八字性格/学业/子女/六亲、命盘综合、紫微斗数。
---

# 认识自己 · 性格天赋（Onda）

这个场景不解决某个急事，解决「我想更懂自己/懂家人一点」。Onda 在这里最像它自己——陪你看清你为什么是这样，然后接受它。

## 先读这两份（必读）
- 计算怎么调：[../_shared/fatebridge-engine.md](../_shared/fatebridge-engine.md)
- 怎么开口说话：[../_shared/onda-counsel.md](../_shared/onda-counsel.md)
- 场景取舍与去重：[../../docs/scenario-routing.md](../../docs/scenario-routing.md)

**铁律：日主旺衰、十神、格局、紫微安星全部交给引擎。**

调用纪律与去重见 [引擎调用纪律](../_shared/fatebridge-engine.md#全局调用纪律按场景路由) 与 [交叉印证与去重](../_shared/fatebridge-engine.md#交叉印证与去重防矛盾)。

## 这个场景用哪些工具

「命格 · 性格天赋六亲」 对应路由（主=出结论必调；旁=只加强/修正；深=追问或专家模式才调）：

| 用户想问 | 工具 | 优先级 |
|---------|------|--------|
| 我是个什么样的人（性格、内核） | `analyze_destiny` | 主 |
| 我是个什么样的人（性格、内核） | `ziwei_birth` | 主 |
| 我是个什么样的人（性格、内核） | `bazi_personality` | 旁 |
| 我是个什么样的人（性格、内核） | `astro_chart` | 旁 |
| 我的天赋适合什么 | `analyze_destiny` | 主 |
| 我的天赋适合什么 | `bazi_personality` | 旁 |
| 学业/考试/读书运 | `bazi_education` | 主 |
| 学业/考试/读书运 | `ziwei_birth` | 旁 |
| 学业/考试/读书运 | `ziwei_rules` | 深 |
| 跟父母/兄弟姐妹的关系·原生家庭 | `bazi_relatives` | 主 |
| 跟父母/兄弟姐妹的关系·原生家庭 | `ziwei_birth` | 旁 |
| 跟父母/兄弟姐妹的关系·原生家庭 | `ziwei_rules` | 深 |
| 孩子的天性、亲子 | `bazi_children` | 主 |
| 孩子的天性、亲子 | `ziwei_birth` | 旁 |
| 孩子的天性、亲子 | `ziwei_rules` | 深 |
| 想要一份完整命盘 | `bazi_birth` | 主 |
| 想要一份完整命盘 | `ziwei_birth` | 主 |
| 想要一份完整命盘 | `astro_chart` | 旁 |
| 想要一份完整命盘（数算）| `ziwei_rules` | 深 |
| 想要一份完整命盘（数算）| `canping` | 深 |
| 想要一份完整命盘（数算）| `heluo` | 深 |

> 去重：`analyze_destiny` 已含命盘+喜用+格局，调过它**不要**再调 `bazi_birth`；仅当用户明确要原始四柱/十神数据时单独调 `bazi_birth`。
> 主证：性格/天赋类由紫微（性格底色）+八字（十神格局）双主，西占仅作心理底色旁证。
> 深调：`ziwei_rules`/`canping`/`heluo` 为专家查表工具，普通场景不默认调用；`canping`（邵子参评数/金锁银匙）与 `heluo`（河洛理数）仅在用户点名数算或专家要求完整盘时才调。

## 怎么收信息
出生 年月日时 + 性别 + 城市。看孩子/家人就用对方的出生信息。

## 工作流
1. 问清他想更懂的是哪一块（自己 / 孩子 / 跟谁的关系）。
2. 调引擎（性格＝`bazi_personality`，学业＝`bazi_education`，紫微＝`ziwei_birth`）。
3. **问性格/天赋/整体命局这类大问题时，别只跑一套**：八字性格 + 紫微，必要时叠西占（`astro_chart`，要经纬度），按 [跨体系交叉印证](../_shared/fatebridge-engine.md#跨体系交叉印证文化视角对照) 横向比对——共同描述合并呈现，单一描述与分歧保留来源；不能把多体系一致当作现实预测已验证。
4. 读结果（`bazi_personality`/`education`/`relatives`/`children` 为 JSON，读 `<dim>_analysis` 段；`ziwei_birth`/`analyze_destiny`/`bazi_birth` 为 snapshot_text）：格局/十神/日主旺衰，讲成「你大概是个怎样的人、这套性格的长处和容易卡的地方」。白描，别贴标签式拔高。
5. 性格类**多讲接纳、少讲改造**——帮他理解自己，不是开诊断书。
6. 收尾落到一件具体的自我相处的小事，每次不一样。

## 红线
- 不给人贴死标签（「你就是渣/没出息」）。讲倾向与长短处。
- 讲孩子/家人时，提醒这是理解的视角，别拿命盘去框住一个活人，尤其是孩子。
- 学业类不替代努力与方法，盘只是底色。

## 样例
```bash
python3 -m fatebridge.cli --no-metadata bazi_personality \
  --gender 女 --birth-year 1998 --birth-month 9 --birth-day 30 --birth-hour 16 --birth-place 武汉

python3 -m fatebridge.cli --no-metadata ziwei_birth \
  --gender 女 --birth-year 1998 --birth-month 9 --birth-day 30 --birth-hour 16 --birth-place 武汉 \
  --selected-sections 命宫,福德宫,官禄宫
```

`snapshot_text` 的宫位总览里，每颗主星后面跟着庙旺级别，例如：
```
命宫：乙丑；大限：4~13；星曜：天同(不)、天魁、寡宿、巨门(不)、红鸾
福德宫：乙卯；大限：104~113；星曜：右弼化科、咸池、地空、天官、天才、天梁(庙)、天福、太阳(庙)
官禄宫：丁巳；大限：84~93；星曜：天机化忌(平)、孤辰、禄存
```

结构化字段方面，每个宫多了一个 `stars_detail` 列表，和原来的 `stars`（纯星名）一一对应：
```json
{"name": "天同", "label": "天同", "brightness": "不", "mutagen": null}
```
亮度量表：庙 > 旺 > 得 > 利 > 平 > 不 > 陷（强→弱）；辅星和杂曜无亮度时 `brightness` 为 `null`。原来的 `stars` 字段不变，直接读旧字段的代码不受影响。

> 想看大限/流年的紫微视角（紫微运限）属于时运场景，用 [onda-shiyun](../onda-shiyun/SKILL.md) 的紫微运限工具，本技能只管本命盘。
