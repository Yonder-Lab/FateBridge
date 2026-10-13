# 虚构用户的对话走查

本记录由当前助手依据真实本地调用结果编写。原始请求与响应保存在同目录 JSON 文件中；没有运行另一位模型，也没有把预期对话写成已完成的 Codex host 对话评测。

## “我想看一下事业，最近要不要跳槽？”

先用 `discover --query 跳槽` 找到 7 项候选，读取事业场景路由后选择 `bazi_career` 作主证。用户提供的虚构资料为演示甲，男，1990-05-15 10:30，北京，Asia/Shanghai；地点坐标和时间都显式保留。第一次调用取必要事业字段，冻结分析时刻；进一步追问时间才加入 `timing_analysis`。

实际 `career_analysis.dominant_ten_gods.primary_career_type` 是“独立经营”，`career_timing` 返回本轮大运与流年规则信号，`timing_context.analysis_date` 是 2026-10-12。

据此可回答：“这套传统规则把你的事业倾向归为‘独立经营’，本轮事业变化信号来自大运、流年字段。它能提供一个自我观察角度，但还不能据此判断你现在这份工作该不该离开。需要把你希望改变的工作内容、现有机会和实际经历一起放进讨论。”不能从“创业倾向”字段直接说用户应该辞职。

原始依据：[事业响应](bazi_career.json)、[裁剪结果](bazi_career-projected.json)、[时运响应](timing_analysis.json)。

## “只记得出生那一天，几点不知道，也能看吗？”

当前出生类模型要求小时。发送空小时实际返回原生 `isError=true`，`issues.path=birth_hour`。不把 `0` 当默认答案，也不继续解释半成品命盘。应先确认用户能否找出时段；无法确认时说明当前接口没有无时盘入口。

同样，2 月 30 日、`birth_minut` 拼写错误和 `day_mastr` 投影拼错都有字段级错误。修正后同一 MCP 连接再次成功，证明错误恢复不要求重启。

原始依据：[报告的 errors 与 error_recovery](report.json)。

## “我俩合不合？为什么有两个分数？”

虚构双方资料调用 `two_person_compatibility`，综合分是 51.1。该分数是多维度加权的规则评价；传统刑冲合害净分使用另一套加减口径，不能把两个分数相加、平均，或读成婚姻成功概率。

体验时发现两条完全相同的挑战句挤掉了第二项有效提示。修复后先为各维度选择两条不同的摘要，再跨维度去重；`detailed_analysis` 中逐事件的来源和评分仍保留，51.1 的综合分未变。回答应指出规则口径差异，具体沟通问题仍以双方实际经历为准。

原始依据：[双人关系响应](two_person_compatibility.json)、[裁剪结果](two_person_compatibility-projected.json)。

## “给我看看星盘，结果有多精确？”

`astro_chart` 实际返回上升巨蟹、天顶白羊；`chart_profile.ephemeris_model=swieph`，后端为 `swisseph_api`。这是当前本地环境的实际模型标识，不能推广成所有安装环境都使用同一星历。

继续询问希腊盘时，目录 key `astro_hellen` 现在可以在 CLI、发现与资源读取中解析；实际 MCP 调用名仍是 `astro_hellen_chart`。用户不必猜测后缀，契约给出正式名称。

原始依据：[核心星盘响应](astro_chart.json)、[希腊盘响应](astro_hellen.json)。

## “我想占一卦；别给我一大段看不懂的文字。”

同一虚构问题使用固定时间的梅花示例，返回本卦火泽睽、变卦火雷噬嗑。先按本卦、变卦和摘要裁剪，再把规则输出解释成传统取象。完整原始数据仍留存，不能把这段解释当未来事实。

原来的摘要出现“忌忌强求一致”。修复了共享拼接处，卦义查询、六爻引用与梅花摘要都不再重复前缀；源卦义的 `caution` 字段保留原文。随机六爻示例固定 seed=42，重放前后业务摘要相同。

原始依据：[梅花响应](meihua_analysis.json)、[六爻响应](sixyao.json)、[纯展示快照迁移](golden-display-migration.json)。

## “我想看家里布局，不过现在没有测量朝向。”

基础 `fengshui_directions` 能返回公共方位资料；`status=complete` 只表示这个基础工具完成。实际 `coverage.not_requested_layers` 还列出八宅、砂水、年度星与玄空宅盘。不能把公共方位结果说成这套房已经完成风水分析，也不能从照片猜测磁北或宅向。

原始依据：[方位响应](fengshui_directions.json)。
