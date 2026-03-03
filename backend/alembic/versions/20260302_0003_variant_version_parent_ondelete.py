"""set variant version parent FK on-delete behavior

Revision ID: 20260302_0003
Revises: 20260227_0002
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260302_0003"
down_revision = "20260227_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow campaign deletion when variant version chains exist."""
    with op.batch_alter_table("variant_versions") as batch_op:
        batch_op.drop_constraint("variant_versions_parent_version_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "variant_versions_parent_version_id_fkey",
            "variant_versions",
            ["parent_version_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Restore restrictive parent-version foreign key behavior."""
    with op.batch_alter_table("variant_versions") as batch_op:
        batch_op.drop_constraint("variant_versions_parent_version_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "variant_versions_parent_version_id_fkey",
            "variant_versions",
            ["parent_version_id"],
            ["id"],
        )
