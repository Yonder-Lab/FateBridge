---
name: onda-mingge
description: 用 FateBridge 回答单项性格、天赋、学业、子女或六亲问题，依据相关专项或命盘解释传统倾向。Use when 用户围绕其中一项了解自己或家人；明确要求多维度人生报告或八字紫微西占全面对照时使用 onda-zige。
---

# 认识自己 · 性格天赋（Onda）

这个场景不解决某个急事，解决「我想更懂自己/懂家人一点」。Onda 在这里最像它自己——陪你看清你为什么是这样，然后接受它。

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
> 主证：按所选问题及路由取八字或紫微；完整性格画像需要双体系时再对照，西占仅按需作旁证。表中多个主入口是问题分支，不要求每个简单问题全部调用。
> 深调：`ziwei_rules`/`canping`/`heluo` 为专家查表工具，普通场景不默认调用；`canping`（邵子参评数/金锁银匙）与 `heluo`（河洛理数）仅在用户点名数算或专家要求完整盘时才调。

## 怎么收信息
出生 年月日时 + 性别 + 城市。看孩子/家人就用对方的出生信息。

## 工作流
1. 问清他想更懂的是哪一块（自己 / 孩子 / 跟谁的关系）。
2. 调引擎（性格＝`bazi_personality`，学业＝`bazi_education`，紫微＝`ziwei_birth`）。
3. 完整性格／命局对照才补另一体系，必要时加西占（`astro_chart`，要经纬度），按 [跨体系交叉印证](../_shared/fatebridge-engine.md#跨体系交叉印证文化视角对照) 横向比对。简单单项先答主证，共同描述与分歧保留来源，不能把多体系一致当作现实预测已验证。
4. 首轮读所选工具的结构化字段，专项读 `<dim>_analysis`，命盘读相应命盘字段；完整盘或导出追问才展开 `snapshot_text`。格局／十神／旺衰按传统解释讲长处和困难，不把规则标签写成已证实人格。
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
