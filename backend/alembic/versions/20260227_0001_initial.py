"""initial schema

Revision ID: 20260227_0001
Revises:
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260227_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute the upgrade workflow. This function is part of the module-level runtime flow."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    campaign_objective = sa.Enum("CTR", "ATC", "CONVERSION", name="campaignobjective")
    campaign_status = sa.Enum("DRAFT", "RUNNING", "PAUSED", name="campaignstatus")

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("product_title", sa.String(length=255), nullable=False),
        sa.Column("product_category", sa.String(length=255), nullable=False),
        sa.Column("product_description", sa.String(length=2000), nullable=False),
        sa.Column("objective", campaign_objective, nullable=False),
        sa.Column("audience_segment", sa.String(length=255), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("primary_kpi", sa.String(length=64), nullable=False),
        sa.Column("status", campaign_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    variant_source = sa.Enum("HUMAN", "CODEX_GENERATED", "CODEX_PATCHED", name="variantsource")

    op.create_table(
        "variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("strategy_tag", sa.String(length=64), nullable=False),
        sa.Column("assets_json", sa.JSON(), nullable=False),
        sa.Column("source", variant_source, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    created_by_system = sa.Enum("USER", "CODEX", "SYSTEM", name="createdbysystem")

    op.create_table(
        "variant_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("assets_json", sa.JSON(), nullable=False),
        sa.Column("parent_version_id", sa.Integer(), sa.ForeignKey("variant_versions.id"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_system", created_by_system, nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("variant_id", "version_number", name="uq_variant_version_number"),
    )

    metric_source = sa.Enum("SIMULATED", "IMPORTED", name="metricsource")

    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("add_to_cart", sa.Integer(), nullable=False),
        sa.Column("bounces", sa.Integer(), nullable=False),
        sa.Column("ctr", sa.Numeric(10, 4), nullable=False),
        sa.Column("atc_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("bounce_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("segment_json", sa.JSON(), nullable=True),
        sa.Column("source", metric_source, nullable=False),
    )

    recommendation_status = sa.Enum("PROPOSED", "APPROVED", "REJECTED", "APPLIED", name="recommendationstatus")
    change_type = sa.Enum("COPY", "LAYOUT", "TRUST_SIGNAL", "CTA", "CONFIG", "CODE", name="changetype")

    op.create_table(
        "improvement_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", recommendation_status, nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("change_type", change_type, nullable=False),
        sa.Column("target_component", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("expected_impact_json", sa.JSON(), nullable=False),
        sa.Column("trigger_metrics_snapshot_id", sa.Integer(), sa.ForeignKey("metric_snapshots.id"), nullable=True),
        sa.Column("patch_json", sa.JSON(), nullable=False),
        sa.Column("codex_raw_response_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    event_type = sa.Enum(
        "RECOMMENDATION_CREATED",
        "APPROVED",
        "REJECTED",
        "APPLIED",
        "OUTCOME_RECORDED",
        "METRICS_SIMULATED",
        name="lifteventtype",
    )
    actor_type = sa.Enum("USER", "SYSTEM", "CODEX", name="actortype")

    op.create_table(
        "lift_trace_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "recommendation_id",
            sa.Integer(),
            sa.ForeignKey("improvement_recommendations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("before_metrics_json", sa.JSON(), nullable=True),
        sa.Column("after_metrics_json", sa.JSON(), nullable=True),
        sa.Column("outcome_delta_json", sa.JSON(), nullable=True),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Execute the downgrade workflow. This function is part of the module-level runtime flow."""
    op.drop_table("lift_trace_events")
    op.drop_table("improvement_recommendations")
    op.drop_table("metric_snapshots")
    op.drop_table("variant_versions")
    op.drop_table("variants")
    op.drop_table("campaigns")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
