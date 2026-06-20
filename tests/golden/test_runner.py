"""runner 的覆盖与确定性测试。"""

from tests.fixtures.surface_payloads import REST_POST_CASES
from tests.golden.runner import compute_outputs


def test_runner_covers_every_rest_tool():
    outputs = compute_outputs()
    # 每个 REST 工具都要产出一份规范化文本，数量与 case 数一致。
    assert len(outputs) == len(REST_POST_CASES)
    assert all(isinstance(text, str) and text for text in outputs.values())


def test_outputs_are_deterministic():
    # 进程内连跑两次必须逐字节相同——抓「同一进程内的可变状态泄漏」。
    # 跨机器 / 跨次运行的可复现性，由 canonical 层剔除易变字段保证，并最终由
    # test_golden_master 对committed 基线的 diff 来兜底。
    assert compute_outputs() == compute_outputs()
