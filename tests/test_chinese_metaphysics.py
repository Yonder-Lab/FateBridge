from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    JinkouAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    QimenAnalysisRequest,
    TaiyiAnalysisRequest,
    ZiweiBirthRequest,
    ZiweiRulesRequest,
)
from fastmcp_server import (
    jinkou,
    liureng_gods,
    liureng_runyear,
    qimen,
    taiyi,
    ziwei_birth,
    ziwei_rules,
)
from fatebridge.services.metaphysics import (
    calculate_jinkou_analysis,
    calculate_liureng_gods,
    calculate_liureng_runyear,
    calculate_qimen_analysis,
    calculate_taiyi_analysis,
    calculate_ziwei_birth,
    calculate_ziwei_rules,
)
from fatebridge.utils.helpers import create_person_info


@pytest.fixture(autouse=True)
def clear_horosa_env(monkeypatch):
    for name in (
        "HOROSA_CORE_JS_CLI",
        "HOROSA_SKILL_CLI",
        "HOROSA_SKILL_PYTHONPATH",
        "HOROSA_SKILL_DATA_DIR",
        "HOROSA_RUNTIME_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)


def _write_fake_horosa_core_js_cli(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env node
import process from 'node:process';

const palaceOrder = ['巽', '离', '坤', '震', '中', '兑', '艮', '坎', '乾'];
const taiyiOrder = ['巽', '巳', '午', '未', '坤', '申', '酉', '戌', '乾', '亥', '子', '丑', '艮', '寅', '卯', '辰'];

const qimenCells = palaceOrder.map((palace, index) => ({
  palaceNum: index + 1,
  palaceName: palace,
  diGan: ['丙', '辛', '癸', '丁', '乙', '己', '庚', '壬', '戊'][index],
  tianGan: ['丙', '辛', '癸', '丁', '乙', '己', '庚', '壬', '戊'][index],
  tianXing: ['辅', '英', '芮', '冲', '', '柱', '任', '蓬', '心'][index],
  door: ['杜', '景', '死', '伤', '', '惊', '生', '休', '开'][index],
  god: ['地', '天', '符', '玄', '', '蛇', '虎', '合', '阴'][index],
  isZhiFu: index === 2,
  isZhiShi: index === 2,
}));

const taiyiPalaces = taiyiOrder.map((palace) => ({
  palace,
  items: palace === '卯' ? ['太乙', '计神'] : palace === '坤' ? ['文昌'] : [],
}));

const outputs = {
  qimen: {
    data: {
      realSunTime: '2026-04-04 21:12:04',
      jieqiText: '春分下元',
      yinYangDun: '阳遁',
      juShu: '六',
      juText: '阳遁六局下元',
      fuTou: '甲辰',
      xunShou: '甲辰',
      kongWang: '寅卯',
      zhiFu: '芮禽',
      zhiShi: '死门',
      zhiFuPalace: 3,
      zhiShiPalace: 3,
      cells: qimenCells,
    },
    snapshot_text: '[qimen]'
  },
  taiyi: {
    data: {
      options: {
        styleLabel: '時計太乙',
        accumLabel: '太乙統宗',
        sexLabel: '男',
      },
      rotation: '固定',
      taiyiPalace: '卯',
      skyeyes: '坤',
      homeCal: 24,
      taishui: '午',
      hegod: '卯',
      palaces: taiyiPalaces,
    },
    snapshot_text: '[taiyi]'
  },
  jinkou: {
    data: {
      diFen: '酉',
      topInfo: {
        xunKong: '寅卯',
      },
      siDaKong: '金',
      yongYao: {
        label: '贵神',
        reason: '贵神旺而得令',
      },
      jiangZi: '亥',
      jiangName: '登明',
      yuejiang: '戌',
      guiStartZi: '未',
      guiZi: '丑',
      guiName: '天乙',
      rows: [
        { label: '人元', content: '辛', shenjiang: '-', elem: '金', power: '旺', gan: '-', kong: '—' },
        { label: '贵神', content: '丑', shenjiang: '贵人', elem: '土', power: '旺', gan: '乙', kong: '空亡' },
        { label: '将神', content: '亥', shenjiang: '登明', elem: '水', power: '相', gan: '辛', kong: '—' },
        { label: '地分', content: '酉', shenjiang: '-', elem: '金', power: '休', gan: '-', kong: '四大空亡' },
      ],
      shenshaRows: [
        { label: '人元', value: '天乙贵人' },
        { label: '贵神', value: '贵人入课' },
        { label: '将神', value: '玄武临门' },
      ],
    },
    snapshot_text: '[jinkou]'
  },
};

const tool = process.argv[3];
process.stdout.write(JSON.stringify({ ok: true, tool, ...outputs[tool] }, null, 2));
""",
        encoding="utf-8",
    )
    return path


def _write_fake_horosa_skill_cli(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys

tool = sys.argv[3]
input_payload = json.load(sys.stdin)

liureng_payload = {
    "month_general": {"branch": "戌", "name": "河魁"},
    "board_style": "涉害",
    "board_order": "天盘逆布",
    "kongwang": "辰巳空",
    "xun_head": "甲子",
    "four_lessons": [
        {"index": 1, "upper_branch": "辰", "lower_branch": "戌", "text": "辰加戌", "relation": "官鬼"},
        {"index": 2, "upper_branch": "巳", "lower_branch": "亥", "text": "巳加亥", "relation": "父母"},
        {"index": 3, "upper_branch": "午", "lower_branch": "子", "text": "午加子", "relation": "子孙"},
        {"index": 4, "upper_branch": "未", "lower_branch": "丑", "text": "未加丑", "relation": "妻财"},
    ],
    "three_transmissions": {
        "initial": {"branch": "辰", "relation": "官鬼", "god": "贵人", "ganzhi": "甲子"},
        "middle": {"branch": "午", "relation": "父母", "god": "腾蛇", "ganzhi": "丙寅"},
        "final": {"branch": "申", "relation": "兄弟", "god": "六合", "ganzhi": "戊辰"},
    },
    "overview": ["Horosa liureng snapshot"],
    "meta": {"is_diurnal": False},
}

outputs = {
    "liureng_gods": {
        "liureng": liureng_payload,
        "snapshot_text": "[liureng_gods]",
        "export_snapshot": {"source": "fake-horosa-skill"},
    },
    "liureng_runyear": {
        "liureng": liureng_payload,
        "runyear": {"age": 33, "ganzhi": "丙午", "gender": True},
        "snapshot_text": "[liureng_runyear]",
        "export_snapshot": {"source": "fake-horosa-skill"},
    },
}

response = {
    "ok": True,
    "tool": tool,
    "version": "test",
    "input_normalized": input_payload,
    "data": outputs[tool],
    "summary": [],
    "warnings": [],
}
sys.stdout.write(json.dumps(response, ensure_ascii=False))
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def test_ziwei_birth_request_model_accepts_birth_fields():
    request = ZiweiBirthRequest(
        name="张三",
        gender="男",
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
    )

    payload = request.model_dump()

    assert payload["name"] == "张三"
    assert payload["gender"] == "男"
    assert payload["birth_hour"] == 14
    assert payload["birth_minute"] == 30
    assert payload["birth_timezone"] == "Asia/Shanghai"


def test_cn_analysis_request_models_accept_fields():
    liureng_request = LiuRengGodsRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )
    qimen_request = QimenAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
    )
    taiyi_request = TaiyiAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )
    jinkou_request = JinkouAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
    )
    runyear_request = LiuRengRunyearRequest(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        gender="男",
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
    )
    rules_request = ZiweiRulesRequest(year_stem="甲")

    assert liureng_request.model_dump()["analysis_longitude"] == 121.4737
    assert qimen_request.model_dump()["analysis_hour"] == 21
    assert taiyi_request.model_dump()["gender"] == "男"
    assert jinkou_request.model_dump()["di_fen"] == "酉"
    assert runyear_request.model_dump()["birth_year"] == 1994
    assert rules_request.model_dump()["year_stem"] == "甲"


def test_calculate_ziwei_birth_returns_twelve_palaces():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_ziwei_birth(person)

    assert result["analysis_type"] == "紫微斗数命盘"
    assert result["ziwei_birth"]["engine"] == "fatebridge-offline"
    assert result["ziwei_birth"]["time_algorithm"] in {"直接时间", "真太阳时"}
    assert len(result["ziwei_birth"]["palaces"]) == 12
    assert result["ziwei_birth"]["ming_gong"]["name"] == "命宫"
    assert result["ziwei_birth"]["shen_gong"]["name"] == "身宫"
    assert set(result["ziwei_birth"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert any("紫微" in "、".join(palace["stars"]) for palace in result["ziwei_birth"]["palaces"])


def test_calculate_ziwei_rules_supports_year_stem_filter():
    result = calculate_ziwei_rules(year_stem="甲")

    assert result["analysis_type"] == "紫微规则库"
    assert result["engine"] == "fatebridge-offline"
    assert result["requested_year_stem"] == "甲"
    assert result["focused_rules"]["year_stem"] == "甲"
    assert set(result["focused_rules"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert "palace_sequence" in result["rule_catalogue"]


def test_calculate_liureng_gods_returns_core_sections():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "大六壬起课"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["liureng"]["month_general"]["branch"]
    assert len(result["liureng"]["four_lessons"]) == 4
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]
    assert result["liureng"]["overview"]
    assert "空" in result["liureng"]["kongwang"]


def test_calculate_liureng_runyear_uses_birth_context():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_liureng_runyear(
        person,
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
    )

    assert result["analysis_type"] == "大六壬行年"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["runyear"]["engine"] == "fatebridge-offline"
    assert result["runyear"]["age"] > 0
    assert len(result["runyear"]["ganzhi"]) == 2
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]


def test_calculate_qimen_analysis_returns_nine_palaces():
    result = calculate_qimen_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "奇门遁甲"
    assert result["qimen"]["dun_type"] in {"阳遁", "阴遁"}
    assert len(result["qimen"]["palaces"]) == 9
    assert result["qimen"]["zhifu"]["star"]
    assert result["qimen"]["zhishi"]["door"]
    assert result["qimen"]["palaces"][0]["door_hexagram"]["name"]


def test_metaphysics_true_solar_time_uses_horosa_compatible_correction():
    result = calculate_qimen_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )

    assert result["analysis_context"]["time_algorithm"] == "真太阳时"
    assert result["analysis_context"]["corrected_datetime"].startswith(
        "2026-04-04 21:12:"
    )
    assert result["analysis_context"]["total_correction_minutes"] == pytest.approx(
        -5.89, abs=0.05
    )


def test_calculate_taiyi_analysis_returns_sixteen_palaces():
    result = calculate_taiyi_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "太乙神数"
    assert result["taiyi"]["style_label"]
    assert result["taiyi"]["taiyi_palace"]
    assert len(result["taiyi"]["palace_marks"]) == 16
    assert result["taiyi"]["core_board"]["main_calculation"]


def test_calculate_jinkou_analysis_returns_four_positions():
    result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "金口诀"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["jinkou"]["engine"] == "fatebridge-offline"
    assert result["jinkou"]["overview"]["di_fen"] == "酉"
    assert len(result["jinkou"]["rows"]) == 4
    assert result["jinkou"]["overview"]["yuejiang"]["name"]
    assert result["jinkou"]["overview"]["guishen"]["name"]
    assert result["jinkou"]["shensha"]


def test_fastmcp_tools_expose_new_parameters():
    assert "birth_year" in ziwei_birth.parameters["properties"]
    assert "year_stem" in ziwei_rules.parameters["properties"]
    assert "analysis_year" in liureng_gods.parameters["properties"]
    assert "birth_year" in liureng_runyear.parameters["properties"]
    assert "analysis_year" in qimen.parameters["properties"]
    assert "gender" in taiyi.parameters["properties"]
    assert "di_fen" in jinkou.parameters["properties"]


def test_services_can_delegate_to_horosa_core_js_when_configured(
    tmp_path, monkeypatch
):
    fake_cli = _write_fake_horosa_core_js_cli(tmp_path / "fake_horosa_core_js.mjs")
    monkeypatch.setenv("HOROSA_CORE_JS_CLI", str(fake_cli))

    qimen_result = calculate_qimen_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )
    taiyi_result = calculate_taiyi_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )
    jinkou_result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        use_true_solar_time=True,
    )

    assert qimen_result["qimen"]["engine"] == "horosa-core-js"
    assert qimen_result["qimen"]["ju_text"] == "阳遁六局下元"
    assert qimen_result["qimen"]["xun_head"] == "甲辰"
    assert len(qimen_result["qimen"]["palaces"]) == 9
    assert qimen_result["qimen"]["palaces"][0]["door_hexagram"]["name"]

    assert taiyi_result["taiyi"]["engine"] == "horosa-core-js"
    assert taiyi_result["taiyi"]["taiyi_palace"] == "卯"
    assert taiyi_result["taiyi"]["wenchang_palace"] == "坤"
    assert taiyi_result["taiyi"]["core_board"]["main_calculation"] == "24局"
    assert len(taiyi_result["taiyi"]["palace_marks"]) == 16

    assert jinkou_result["jinkou"]["engine"] == "horosa-core-js"
    assert jinkou_result["jinkou"]["overview"]["use_position"] == "贵神"
    assert jinkou_result["jinkou"]["overview"]["guishen"]["name"] == "天乙"
    assert len(jinkou_result["jinkou"]["rows"]) == 4
    assert jinkou_result["jinkou"]["shensha"][0]["value"] == "天乙贵人"


def test_services_can_delegate_to_horosa_skill_cli_when_configured(
    tmp_path, monkeypatch
):
    fake_skill_cli = _write_fake_horosa_skill_cli(tmp_path / "fake_horosa_skill_cli.py")
    fake_core_js_cli = _write_fake_horosa_core_js_cli(tmp_path / "fake_horosa_core_js.mjs")
    monkeypatch.setenv("HOROSA_SKILL_CLI", str(fake_skill_cli))
    monkeypatch.setenv("HOROSA_CORE_JS_CLI", str(fake_core_js_cli))

    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    liureng_result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )
    runyear_result = calculate_liureng_runyear(
        person,
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )
    jinkou_result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        use_true_solar_time=True,
    )

    assert liureng_result["liureng"]["engine"] == "horosa-skill-cli"
    assert liureng_result["liureng"]["month_general"]["branch"] == "戌"
    assert liureng_result["liureng"]["snapshot_text"] == "[liureng_gods]"
    assert "_raw_liureng" not in liureng_result["liureng"]

    assert runyear_result["liureng"]["engine"] == "horosa-skill-cli"
    assert runyear_result["runyear"]["engine"] == "horosa-skill-cli"
    assert runyear_result["runyear"]["ganzhi"] == "丙午"
    assert "_raw_liureng" not in runyear_result["liureng"]

    assert jinkou_result["liureng"]["engine"] == "horosa-skill-cli"
    assert jinkou_result["liureng"]["month_general"]["branch"] == "戌"
    assert jinkou_result["jinkou"]["engine"] == "horosa-core-js"
    assert jinkou_result["jinkou"]["overview"]["guishen"]["name"] == "天乙"
