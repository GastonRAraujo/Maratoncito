"""Initial domain persistence scaffolding.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("year", sa.Integer()),
        sa.Column("tmdb_id", sa.Integer()),
        sa.Column("tvdb_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "tmdb_id", name="uq_media_kind_tmdb"),
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.String(length=128)),
        sa.Column("overrides_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "download_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("media_id", sa.String(length=36), sa.ForeignKey("media_items.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("client_hash", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("download_jobs")
    op.drop_table("profiles")
    op.drop_table("media_items")
