"""add recommendation feedback

Revision ID: 20260227_0002
Revises: 20260227_0001
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260227_0002"
down_revision = "20260227_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute the upgrade workflow. This function is part of the module-level runtime flow."""
    feedback_sentiment = sa.Enum("POSITIVE", "NEGATIVE", name="feedbacksentiment")
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recommendation_id", sa.Integer(), sa.ForeignKey("improvement_recommendations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sentiment", feedback_sentiment, nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recommendation_feedback_campaign_id", "recommendation_feedback", ["campaign_id"], unique=False)


def downgrade() -> None:
    """Execute the downgrade workflow. This function is part of the module-level runtime flow."""
    op.drop_index("ix_recommendation_feedback_campaign_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
