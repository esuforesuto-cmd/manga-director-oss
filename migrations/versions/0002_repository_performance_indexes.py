"""Add composite page indexes for selective large-project repository reads.

Revision ID: 0002_repository_performance_indexes
Revises: 0001_initial
Create Date: 2026-07-26
"""

from __future__ import annotations

from alembic import op

revision = "0002_repository_performance_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Support Project/page lookup and state-filter query patterns."""

    op.create_index("ix_pages_project_page_number", "pages", ["project_id", "page_number"])
    op.create_index("ix_pages_project_state", "pages", ["project_id", "state"])


def downgrade() -> None:
    """Remove v2.2 additive indexes only."""

    op.drop_index("ix_pages_project_state", table_name="pages")
    op.drop_index("ix_pages_project_page_number", table_name="pages")
