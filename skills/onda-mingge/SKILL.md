---
name: onda-mingge
description: 用 FateBridge 回答单项性格、天赋、学业、子女或六亲问题，把相关命盘或专项的不同依据转成可与真实经历对照的特点和一项小尝试。Use when 用户围绕其中一项了解自己或家人；明确要求多维度人生报告或八字紫微西占全面对照时使用 onda-zige。不把人格、学历或家人关系写成定论。
---

# 认识自己 · 性格天赋（Onda）

这个场景围绕「我想更懂自己／懂家人一点」，把计算中的差异讲清，让用户用自己的经历辨认哪些说法贴近，而不是把传统标签当成人格结论。

## 用户能得到什么

只交付本次所问的一项。选 2–3 个相关依据，讲一处可发挥的特点、一处需要条件的表现，再给一个可从日常反馈观察的小尝试；详细对照才用短表。

| 本次问题 | 实际计算提供什么 | 给用户的用处与限度 |
| --- | --- | --- |
| 性格／天赋 | 本命结构；专项 `personality_analysis` 的 `dominant_traits`、`disposition`、`strengths`、`weaknesses` | 把不同倾向放进用户已说的任务或相处场景，邀请对照真实例子；不是心理测评、能力鉴定或身份标签 |
| 学习／考试 | `education_analysis.study_stars`、`subject_orientation`、`exam_timing` 与 `timing_context` | 将传统偏向转成学习方法的尝试，例如对比整理知识与限时练习后的反馈；学历层级分数不代表录取率或学历上限 |
| 孩子本人的性格／学习 | 用孩子资料计算本命结构、性格或学业专项 | 与孩子实际表现对照，不从父母的子女宫推断孩子人格或学习能力 |
| 命主的子女缘／六亲文化 | 用该命主资料读取 `children_analysis`／`relatives_analysis` 中实际返回的子项 | 明确这是命主视角；从具体沟通反馈核对，不推断生育能力、子女性别或家人的想法 |
| 指定紫微视角 | 所问宫位的实际星曜、`stars_detail`、四化等已返回数据 | 讲相关星曜组合的传统含义和限制；不从单颗星判人格，缺哪层就保留哪层 |

学习方法与沟通尝试是现实建议，不是引擎验证过的效果。若用户反馈与传统描述不符，记录不贴合之处，不用另一套标签强行解释；只解释同一结果时不重算。

## 引用路径

发现入口可能是软链接。优先进入入口目录后用 shell 内建 `pwd -P` 取得真实目录，再按它读取下面的相对引用；不要为解析路径调用未经核实的系统 `python3`。不能先裁剪 `.agents/skills/onda-*` 入口的字符串父目录，否则会误指到 `.agents/skills/_shared` 或 `.agents/docs`。读取已知引用无需搜索仓库。

## 先读这两份（必读）
- 计算怎么调：[../_shared/fatebridge-engine.md](../_shared/fatebridge-engine.md)
- 怎么开口说话：[../_shared/onda-counsel.md](../_shared/onda-counsel.md)
- 场景取舍与去重：[../../docs/scenario-routing.md](../../docs/scenario-routing.md)

**铁律：日主旺衰、十神、格局、紫微安星全部交给引擎。**

调用纪律与去重见 [引擎调用纪律](../_shared/fatebridge-engine.md#全局调用纪律) 与 [交叉印证与去重](../_shared/fatebridge-engine.md#交叉印证与去重防矛盾)。

## 这个场景用哪些工具

「命格 · 性格天赋六亲」对应路由（主=出结论必调；旁=只加强/修正；深=追问或专家模式才调）：

| 用户想问 | 工具 | 优先级 |
|---------|------|--------|
| 我是个什么样的人（性格、内核） | `analyze_destiny` | 主 |
| 我是个什么样的人（性格、内核） | `ziwei_birth` | 主（用户选择紫微时） |
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
| 孩子本人的性格／天赋 | `analyze_destiny` | 主（用孩子资料） |
| 孩子本人的性格专项／学习 | `bazi_personality` / `bazi_education` | 按所问内容选择（用孩子资料） |
| 命主的子女缘／子女宫 | `bazi_children` | 主（用命主资料） |
| 命主的子女缘／子女宫 | `ziwei_birth` | 旁 |
| 命主的子女缘／子女宫 | `ziwei_rules` | 深 |
| 想要一份完整命盘 | `bazi_birth` | 主 |
| 想要一份完整命盘 | `ziwei_birth` | 主 |
| 想要一份完整命盘 | `astro_chart` | 旁 |
| 想要一份完整命盘（数算）| `ziwei_rules` | 深 |
| 想要一份完整命盘（数算）| `canping` | 深 |
| 想要一份完整命盘（数算）| `heluo` | 深 |

> 去重：`analyze_destiny` 已含命盘+喜用+格局，调过它**不要**再调 `bazi_birth`；仅当用户明确要原始四柱/十神数据时单独调 `bazi_birth`。
> 主证：按所选问题及路由取八字或紫微；完整性格画像需要双体系时再对照，西占仅按需作旁证。表中多个主入口是问题分支，不要求每个简单问题全部调用。
> 深调：`ziwei_rules`/`canping`/`heluo` 为专家查表工具，普通场景不默认调用；`canping`（邵子参评数/金锁银匙）与 `heluo`（河洛理数）仅在用户点名数算或专家要求完整盘时才调。

## 怎么收信息
出生 年月日时 + 性别 + 城市。分析孩子／家人本人的性格、学习时用那个人的资料；分析“我的子女缘／我与六亲的传统对应”时用“我”的资料。`bazi_children` 的子女星和子女宫来自命主自己的盘，不是孩子的性格盘；`bazi_relatives` 同样是命主视角。

## 工作流
1. 按已确认的问题确定对象是自己、孩子本人还是命主的六亲对应；只有对象不清时再简短核对。
2. 性格／天赋默认以 `analyze_destiny` 为基础，用户选择紫微则用 `ziwei_birth`；已有主命盘或明确需要性格专项细节时才补 `bazi_personality`。学业用 `bazi_education`；孩子本人同样按问题使用其资料。命主的子女缘／六亲文化分别用 `bazi_children`／`bazi_relatives`，不为单项问题默认开三套体系。
3. 完整性格／命局对照才补另一体系，必要时加西占（`astro_chart`，核心盘可由引擎解析支持的出生城市），按 [跨体系交叉印证](../_shared/fatebridge-engine.md#跨体系交叉印证文化视角对照) 横向比对。简单单项先答主证，共同描述与分歧保留来源，不能把多体系一致当作现实预测已验证。
4. 首轮读所选工具的结构化字段，专项读 `<dim>_analysis`，命盘读相应命盘字段；完整盘或导出追问才展开 `snapshot_text`。格局／十神／旺衰按传统解释讲长处和困难，不把规则标签写成已证实人格。
5. 性格类尊重用户对自己的认识：把优势和困难放在发生条件里，不要求用户认同传统描述。学业和亲子解释同样以现实表现为准。
6. 给一项与本次特点有关、可得到反馈的小尝试；已有建议就自然停下，不为结尾再加任务。

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
  --selected-sections 宫位总览
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
