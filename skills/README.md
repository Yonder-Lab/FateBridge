# FateBridge · 公开 Skills 汇总

本目录收录与 FateBridge 命理/占术领域相关的公开 Claude Code Skills，供 Agent 工具接入时直接引用。

---

## 目录结构

```
skills/
├── bazi/               八字四柱排盘与命理分析（jinchenma94/bazi-skill）
├── yinyuan/            姻缘测算 · 赛博月老（Ming-H/yinyuan-skills）
└── numerologist/       数术工程化三件套（FANzR-arch/Numerologist_skills）
    ├── bazi/           —— 四柱八字大师
    ├── ziwei-doushu/   —— 紫微斗数大师
    └── qimen-dunjia/   —— 奇门遁甲大师
```

---

## 已收录 Skills

| 技能 | 来源仓库 | 覆盖系统 | 许可证 |
|------|---------|---------|--------|
| [八字四柱命理分析](./bazi/SKILL.md) | [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill) | 八字、大运流年 | MIT |
| [姻缘测算](./yinyuan/SKILL.md) | [Ming-H/yinyuan-skills](https://github.com/Ming-H/yinyuan-skills) | 八字合婚、生肖配对、紫微夫妻宫、桃花运 | — |
| [数术·八字大师](./numerologist/bazi/SKILL.md) | [FANzR-arch/Numerologist_skills](https://github.com/FANzR-arch/Numerologist_skills) | 四柱八字（工程化） | — |
| [数术·紫微斗数大师](./numerologist/ziwei-doushu/SKILL.md) | [FANzR-arch/Numerologist_skills](https://github.com/FANzR-arch/Numerologist_skills) | 紫微斗数 | — |
| [数术·奇门遁甲大师](./numerologist/qimen-dunjia/SKILL.md) | [FANzR-arch/Numerologist_skills](https://github.com/FANzR-arch/Numerologist_skills) | 奇门遁甲 | — |

---

## 相关项目（非 Skill，供参考）

| 项目 | 仓库 | 类型 | 说明 |
|------|------|------|------|
| horosa-skill | [Horace-Maxwell/horosa-skill](https://github.com/Horace-Maxwell/horosa-skill) | Python 包（同类后端） | 与 FateBridge 功能高度重叠：涵盖 Ziwei、Bazi、Qimen、西占全套；AGPL-3.0 授权，可作算法对比参考 |
| cyber-fortune-telling | [zhaoolee/cyber-fortune-telling](https://github.com/zhaoolee/cyber-fortune-telling) | Web 应用 | Next.js + Strapi 全栈风水命理应用，含 MCP Server；可作前端集成参考 |
| Master-skill | [xr843/Master-skill](https://github.com/xr843/Master-skill) | Claude Code Skill | 佛学大师教学角色生成器（玄奘、慧能等八位），与命理体系交叉度低，不纳入主目录 |

> 小红书链接（7-10）因平台访问限制无法自动抓取，请手动查阅后按上方格式补充。

---

## 使用方式

在 Claude Code 中通过 Skill 工具按路径调用，例如：

```
skill: "skills/bazi"
skill: "skills/yinyuan"
skill: "skills/numerologist/qimen-dunjia"
```

或在 Agent 提示中直接引用对应 SKILL.md 的相对路径。

---

## 贡献指南

如需新增社区技能：
1. 在对应术数子目录下创建 `SKILL.md`（参照现有格式）
2. 在本 README 的"已收录 Skills"表格中补充一行
3. 注明来源仓库、覆盖系统与许可证
