"""Shared descriptions of transport output controls."""

COMPACT_FLAG_DESC = "紧凑 JSON 输出（无缩进）；设为 false 则美化缩进。默认 true。"
SNAPSHOT_FLAG_DESC = (
    "是否包含人类可读的 snapshot_text 文本段（默认随工具而定）；"
    "设为 false 可显著减少返回的 token 数。"
)
FIELDS_FLAG_DESC = (
    "仅返回选定字段以节省 token：接受顶层键（如 'snapshot_text'）或点路径"
    "子字段（如 'bazi_birth.day_master'）。run_metadata 始终保留；留空返回全部字段。"
    "无效路径默认附 projection_warnings；strict_fields=true 时拒绝。"
)
STRICT_FIELDS_DESC = "是否拒绝无效 fields 路径；默认 false，使用宽松投影并返回警告。"
