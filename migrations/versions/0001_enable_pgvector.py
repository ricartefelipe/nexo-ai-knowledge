"""enable the pgvector extension

Revision ID: 0001_enable_pgvector
Revises:
Create Date: 2026-10-12

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_enable_pgvector"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Install pgvector in the current database. Embedding tables arrive in a later release."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Remove pgvector only when nothing in this database depends on it.

    ``DROP EXTENSION`` is issued without ``CASCADE``. PostgreSQL rejects the statement
    when tables, columns, or other objects still depend on the extension.
    """

    op.execute("DROP EXTENSION IF EXISTS vector")
