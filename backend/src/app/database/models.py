from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
)

metadata = MetaData()

fact_product = Table(
    "fact_product",
    metadata,
    Column("product_id", Integer, primary_key=True),
    Column("product_name", String(255), nullable=False),
    Column("os_version", Text),
    Column("language_support", Text),
    Column("price", Integer),
    Column("picture_url", String(255)),
    Column("created_at", TIMESTAMP, server_default=func.current_timestamp()),
)


def build_dim_table(table_name: str, extra_columns: list[Column]) -> Table:
    return Table(
        table_name,
        metadata,
        Column("dim_id", Integer, primary_key=True),
        Column("product_id", Integer, ForeignKey("fact_product.product_id"), nullable=False),
        *extra_columns,
        Column("youtuber_review", Text),
        Column("user_review", Text),
        Column("last_updated", TIMESTAMP, server_default=func.current_timestamp()),
    )


dim_display = build_dim_table(
    "dim_display",
    [
        Column("display_type", String(100)),
        Column("color_depth", String(50)),
        Column("display_standard", Text),
        Column("resolution", Text),
        Column("screen_size", Text),
        Column("touch_technology", String(255)),
    ],
)

dim_camera = build_dim_table(
    "dim_camera",
    [
        Column("rear_camera", Text),
        Column("front_camera", Text),
        Column("flash_light", Text),
        Column("camera_features", Text),
        Column("video_recording", Text),
        Column("video_call", Text),
    ],
)

dim_performance = build_dim_table(
    "dim_performance",
    [
        Column("cpu_speed", Text),
        Column("core_count", Text),
        Column("chipset", Text),
        Column("ram_capacity", Text),
        Column("gpu_chip", String(255)),
    ],
)

dim_storage = build_dim_table(
    "dim_storage",
    [
        Column("phonebook_storage", String(255)),
        Column("internal_storage", Text),
        Column("external_memory", String(255)),
        Column("max_external_support", String(255)),
    ],
)

dim_design = build_dim_table(
    "dim_design",
    [
        Column("design_style", Text),
        Column("dimensions", String(255)),
        Column("weight", Text),
    ],
)

dim_battery = build_dim_table(
    "dim_battery",
    [
        Column("battery_type", String(255)),
        Column("battery_capacity", Text),
        Column("removable_battery", Text),
    ],
)

dim_connectivity = build_dim_table(
    "dim_connectivity",
    [
        Column("network_3g", Text),
        Column("network_4g", Text),
        Column("sim_type", String(255)),
        Column("sim_slots", String(255)),
        Column("wifi", Text),
        Column("gps", Text),
        Column("bluetooth", String(255)),
        Column("gprs_edge", Text),
        Column("headphone_jack", String(255)),
        Column("nfc", Text),
        Column("usb_connection", String(255)),
        Column("other_connections", Text),
        Column("charging_port", Text),
    ],
)

dim_utilities = build_dim_table(
    "dim_utilities",
    [
        Column("movie_playback", Text),
        Column("music_playback", Text),
        Column("charging_port_alt", Text),
        Column("voice_recorder", Text),
        Column("fm_radio", Text),
        Column("other_features", Text),
    ],
)

dim_video_transcripts = Table(
    "dim_video_transcripts",
    metadata,
    Column("video_id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("fact_product.product_id")),
    Column("youtube_url", Text, unique=True),
    Column("s3_audio_path", Text),
    Column("s3_transcript_path", Text),
    Column("s3_comments_path", Text),
    Column("raw_transcript", Text),
    Column("created_at", TIMESTAMP, server_default=func.current_timestamp()),
)

dim_video_comments = Table(
    "dim_video_comments",
    metadata,
    Column("comment_id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("dim_video_transcripts.video_id")),
    Column("comment_text", Text),
    Column("user_name", String(255)),
    Column("created_at", TIMESTAMP, server_default=func.current_timestamp()),
)

Index("idx_fact_product_name", fact_product.c.product_name)
Index("idx_transcript_product", dim_video_transcripts.c.product_id)
Index("idx_comment_video", dim_video_comments.c.video_id)
