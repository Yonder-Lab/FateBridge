# FateBridge 计算修复与复核（2026-10-09）

已修复初轮审计中能裁定的农历、紫微运限、六壬取传/布将和真太阳时入口问题，并实际重跑第三方引擎。原始审计保留在 [REPORT.md](REPORT.md)，修复后原始结果在 [post-fix/](post-fix/)。结论仅覆盖下表的字段与规则，不代表所有工具及解释文字已获准确性认证。

| 项目 | 修复内容 | 修复后外部复核 |
| --- | --- | --- |
| 农历 | 更正 lunardate 0.2.2 的 1933、1954、1978 年月长编码；保留年界、不修改依赖全局表；缓存不可变转换值 | sxtwl 2.0.7 对支持范围 1900-01-31 至 2100-02-08 逐日核验：73,058 天，0 差异，原为 90 天不同 |
| 紫微 | 按农历年计算虚岁、流年、小限；补齐斗君流月及流日、流时旋转；修复童限；区分实际宫干支与四化天干 | iztro 2.5.8 对齐规则后，400 组本命与运限的已比较字段均为 0 差异；另保存 18 组边界交叉测试 |
| 六壬三传 | 首课生克使用日干五行；按九宗门处理贼克、比用、涉害、遥克、昴星、别责、八专、伏吟、返吟 | 独立 daliurenpython 实际运行：60 日干支 × 12 时支 × 12 月将，共 8,640 种组合、720 种独立天地盘，三传 0 差异、0 异常 |
| 六壬布将 | 以贵人实际地盘落位定顺逆，并把天盘天将正确映射到地盘；同步依赖它的金口诀与三式结果 | 同输入 kinliuren 240 组：月将、天地盘、四课上神、地盘天将均 0 差异 |
| 真太阳时 | 奇门、六壬、太乙、金口诀共享入口补上均时差，与本命入口统一 | Skyfield 1.55 + JPL DE440s 的 3 组太阳时角对照，时支全部一致；保留近似均时差算法，最大时刻误差约 24.12 秒 |

## 公开 API 的原始复现已复测

通过本地 FastAPI TestClient 重放原审计的四个请求，均为 HTTP 200，且断言修复值正确。完整请求与返回见 [rest_reproductions.json](post-fix/rest_reproductions.json)。

- 1954-12-01 农历由冬月初六改为 **冬月初七**。
- 1990-05-15 10:00 男命，目标 2026-10-09 10:00：紫微流月/流日/流时实际落宫由戌/辰/巳改为 **卯/未/子**。
- 2026-09-01 10:00 戊寅日伏吟：三传由巳→寅→巳改为 **巳→申→寅**。
- 2026-11-03 00:50、+08:00、东经 120°、开启真太阳时：奇门修正时间为 **01:06:21、己丑时**；Skyfield 约为 01:06:26.6。

## 紫微规则和参考范围

本命返回新增 `lunar_date`、`hour_branch`、`calendar_rules`；运限也返回规则。春节为紫微年界；晚子时本命农历日期算当天；闰月十五日及以前算当月，之后算下月。iztro 显式配置 `yearDivide/horoscopeDivide/ageDivide='normal'`、`dayDivide='current'`，从运限 `.index` 取实际本命宫。

400 组比较包括命身宫、五行局、宫名/宫干、大限区间、63 颗共同星曜的位置/亮度/四化、虚岁及六种运限落宫/四化。iztro 额外的天空、截路、空亡不在共同星曜范围内。默认晚子换次日仍有 80 张本命不同，这是约定差异，保留既有当天口径。童限不再误回退到老年大限；不支持的农历日期或负虚岁明确返回 400。

运限 `branch` 是实际落宫，新增 `palace_ganzhi` 是该本命宫干支，`stem` 是四化所用天干。二者不能直接拼接成一组历法干支。快照文字也据此修正。交叉测试基准由实际 JS iztro 2.5.8 生成，涵盖春节/立春之间、晚子、童限、出生与目标闰月、历史农历修正日期。

## 审查后追加：保留实际发用课序

修正按首传上神反查第一条匹配课造成的误标。取传算法现在直接返回实际选中的课序；贼克、比用、涉害和遥克保留所选课，伏吟保留实际日干/日支起课，昴星等四课之外推导的首传不再因上神重名误标一课。

2026-09-08 20:00、关闭真太阳时、金口诀地分为丑时，第一、第四课上神同为亥，但比用实际取第四课的「下贼上」。公开 API 回归验证发用为第四课、仅第四课标记 `use_candidate`，金口诀用神为「地分」。全部 8,640 种组合仍与独立三传基准一致，并新增发用元数据一致性检查。完整回归为 **934 passed、82 skipped、3 warnings**，类型和格式检查通过；四份涉及六壬的 golden 样例原生输出未发生变化，无需追加改写快照。

追加复核日志与该 API 原始返回见 `post-fix/review-fix-*`，最新源码哈希见 [review-fix-environment.json](post-fix/review-fix-environment.json)，复核来源与结果哈希见 [review-fix-provenance.json](post-fix/review-fix-provenance.json)。此前结果文件保留原修复阶段的证据。

## 六壬参考的裁定

扩核发现最初的 kinliuren 参考自身不稳定：同一日干支与同一天地盘，仅同时旋转时支和月将，其三传可能改变；全组合运行也会抛异常。原审计“102 组不同”不能全部直接判为 FateBridge 错误。参考异常及同盘变化保存在 [kinliuren_consistency.json](post-fix/kinliuren_consistency.json)。

因此三传以另一独立实现复核。脚本加载该参考原有的 `TianPan/SiKe/SanChuan` 等类定义和其干支五行对象，排除 UI/历法入口，未修改参考数学逻辑，未用 FateBridge 函数替换参考计算，也未将参考源码引入生产依赖。固定来源为 [daliurenpython 提交 2afe919](https://github.com/d1210182010/daliurenpython-zh-tw/tree/2afe9194e3644d2ead5652ed8b366ae6c70d7087) 及 [干支五行依赖提交 0efdcc5](https://github.com/wlhyl/ganzhiwuxinForPython/tree/0efdcc5c473487ef61b2e941005716056174cc54)。

[独立复核结果](post-fix/liuren_independent.json) 与 720 张参考盘基准已持久化，测试再遍历全部 8,640 种输入。修复后三传仍有 36/240 组与旧 kinliuren 不同；此差异如实保留，未为迎合有异常的参考改写结果。本次三传验证不包含所有神煞、课体解释、流派差异或金口诀的完整独立认证。

## 回归、基准与剩余范围

完整测试 **933 passed、82 skipped、3 warnings**；mypy 检查 105 个生产文件通过，Black、isort、`git diff --check` 通过。日志见 [pytest.txt](post-fix/pytest.txt) 和 [mypy.txt](post-fix/mypy.txt)。当前 macOS ARM / Python 3.13 下有 81 项 Linux x86_64 / Python 3.12 固定环境 golden 字节比较跳过，不能据此声称 Linux CI 已验收。

只更新六份涉及此次计算修复的 golden 快照：在同一解释器和相同 Swiss 星历下比较修改前后源码，只更新确认变化的 JSON 路径，平台差异字段保留；详见 [golden_updates.json](post-fix/golden_updates.json)。没有通过整批重生成来覆盖未解释的变化。

再次复核的八字四柱 2,458 组、大运 200 组仍通过；西占位置、上升/天顶、日月返仍在原审计容差内。**太乙仍有 59/100 组与当前 kintaiyi 的版本差异**，暂未替换算法；需要先裁定典籍、表格和采用版本。真太阳时保留近似算法，上述秒级残差意味着极贴近时辰边界的输入仍需更高精度裁定。完整奇门、金口诀、其他未覆盖算法和解释/评分的验证范围仍以原报告为准。

改动在本地工作区，未增加生产计算依赖。测试与 API 复现不等于线上部署或前端验收。审计期间其他聊天更新了文档和界面提交，生产计算源码在这些提交之间未变；修复后的实际工作区源码逐文件哈希见 [environment.json](post-fix/environment.json)，参考版本与结果哈希见 [provenance.json](post-fix/provenance.json)。

## 重跑

第三方依赖、参考 Git 仓库及星历放在仓库外的 `/tmp/fatebridge-audit-20261009`。临时目录可能被清理；新环境需按原审计与上文固定版本重新准备。

```sh
PYTHONPATH=/tmp/fatebridge-audit-20261009/python:/tmp/fatebridge-audit-20261009/kintaiyi/src \
.venv/bin/python scripts/audit_third_party.py \
  --out docs/audits/2026-10-09/post-fix \
  --iztro /tmp/fatebridge-audit-20261009/node/node_modules/iztro \
  --ephemeris /tmp/fatebridge-audit-20261009/de440s.bsp \
  --with-kintaiyi
.venv/bin/python scripts/audit_liureng_independent.py \
  --reference /tmp/fatebridge-audit-20261009/daliurenpython \
  --ganzhi /tmp/fatebridge-audit-20261009/ganzhiwuxin-python \
  --out docs/audits/2026-10-09/post-fix/liuren_independent.json
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q
.venv/bin/python -m mypy src/fatebridge
.venv/bin/python -m black --check src/fatebridge scripts tests
.venv/bin/python -m isort --check-only src/fatebridge scripts tests
git diff --check
```
