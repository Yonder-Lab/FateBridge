import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.core.sukuyo import (
    RELATION_TEMPLATE,
    SU27_ORDER,
    relation_between_su27,
    su28_to_su27,
    sukuyo_relation,
)
from fatebridge.services.divination import calculate_sukuyo_compatibility


def test_su27_order_drops_niu_and_keeps_27():
    assert "牛" not in SU27_ORDER
    assert len(SU27_ORDER) == 27
    # 角 starts the cycle; 斗 immediately precedes 女 (牛 removed in between).
    assert SU27_ORDER[0] == "角"
    assert SU27_ORDER[SU27_ORDER.index("斗") + 1] == "女"


def test_worked_example_ming_su_dou_sees_wei_as_qin_near():
    # Cited reference: for 本命宿=斗, 親 falls on 胃(近)/張(中)/箕(遠).
    # https://www.domap.net/uranai/syukuyo/syukuyo-column08/
    result = relation_between_su27("斗", "胃")
    assert result["relation"] == "親"
    assert result["distance"] == "近"
    assert result["pair"] == "栄親"


def test_worked_example_zhang_and_ji_are_qin_at_mid_and_far():
    assert relation_between_su27("斗", "张")["distance"] == "中"
    assert relation_between_su27("斗", "箕")["distance"] == "遠"
    assert relation_between_su27("斗", "张")["relation"] == "親"
    assert relation_between_su27("斗", "箕")["relation"] == "親"


def test_relation_is_directional_and_pairs_with_reverse():
    # 斗 sees 胃 as 親(近); 胃 sees 斗 as 栄(遠); together the 栄親 pair.
    forward = relation_between_su27("斗", "胃")
    reverse = relation_between_su27("胃", "斗")
    assert forward["relation"] == "親"
    assert reverse["relation"] == "栄"
    assert forward["pair"] == reverse["pair"] == "栄親"
    assert reverse["distance"] == "遠"


def test_same_su_is_ming_with_no_distance():
    result = relation_between_su27("角", "角")
    assert result["relation"] == "命"
    assert result["pair"] == "命"
    assert result["distance"] is None


def test_ye_and_tai_are_distance_9_and_18():
    # 27-cycle from 角: position 9 == 虚 (業), position 18 == 觜 (胎).
    assert relation_between_su27("角", "虚")["relation"] == "業"
    assert relation_between_su27("角", "觜")["relation"] == "胎"
    assert relation_between_su27("角", "虚")["pair"] == "業胎"
    assert relation_between_su27("角", "觜")["distance"] is None


def test_su28_to_su27_passthrough_for_normal_mansion():
    assert su28_to_su27("胃") == "胃"
    assert su28_to_su27("角") == "角"


def test_su28_to_su27_handles_niu_edge_by_longitude():
    # 牛宿 spans the 28-equal band [102.857, 115.714); split at its midpoint:
    # earlier half -> preceding 27-mansion 斗, later half -> following 女.
    assert su28_to_su27("牛", longitude=104.0) == "斗"
    assert su28_to_su27("牛", longitude=114.0) == "女"


def test_sukuyo_relation_accepts_su28_names_and_maps():
    result = sukuyo_relation("斗", "胃")
    assert result["self_su27"] == "斗"
    assert result["other_su27"] == "胃"
    assert result["relation"] == "親"
    assert result["distance"] == "近"
    assert result["meaning"]


def test_sukuyo_compatibility_returns_bidirectional_relations():
    result = calculate_sukuyo_compatibility(
        person1_name="甲",
        person1_date="1990-06-15",
        person1_time="08:30:00",
        person1_zone="+08:00",
        person1_lat="31n13",
        person1_lon="121e28",
        person2_name="乙",
        person2_date="1992-03-20",
        person2_time="14:00:00",
        person2_zone="+08:00",
        person2_lat="31n13",
        person2_lon="121e28",
    )

    assert result["analysis_type"].startswith("宿曜")
    assert result["person1"]["natal_su27"] in SU27_ORDER
    assert result["person2"]["natal_su27"] in SU27_ORDER

    forward = result["person1_to_person2"]
    reverse = result["person2_to_person1"]
    assert forward["relation"] in RELATION_TEMPLATE
    assert reverse["relation"] in RELATION_TEMPLATE
    # 同一对关系，正反向看到的配对类型必须一致。
    assert forward["pair"] == reverse["pair"] == result["pair"]
    assert result["summary"]


def test_sukuyo_compatibility_same_birth_is_ming():
    spec = dict(
        date="1990-06-15",
        time="08:30:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
    )
    result = calculate_sukuyo_compatibility(
        person1_name="甲",
        person2_name="乙",
        **{f"person1_{k}": v for k, v in spec.items()},
        **{f"person2_{k}": v for k, v in spec.items()},
    )
    assert result["person1"]["natal_su27"] == result["person2"]["natal_su27"]
    assert result["person1_to_person2"]["relation"] == "命"
    assert result["pair"] == "命"
