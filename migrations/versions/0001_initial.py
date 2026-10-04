"""Initial Project aggregate persistence schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persisted Project, Chapter, and Page records."""

    op.create_table(
        "projects",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "chapters",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(255),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(255),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column("artifacts", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=False),
        sa.Column("history", sa.Text(), nullable=False),
    )
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])
    op.create_index("ix_pages_project_id", "pages", ["project_id"])


def downgrade() -> None:
    """Drop the initial aggregate persistence schema in dependency order."""

    op.drop_table("pages")
    op.drop_table("chapters")
    op.drop_table("projects")
