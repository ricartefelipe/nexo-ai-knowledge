"""record which embedding model and chunking version produced each document

Revision ID: 0003_embedding_versioning
Revises: 0002_create_documents
Create Date: 2026-10-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_embedding_versioning"
down_revision: str | None = "0002_create_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Existing rows keep NULL: they were embedded before versioning and are matched only when
    the running model equals the one that produced them (they are backfilled with the model
    name declared at upgrade time, which is the only model this schema ever accepted)."""

    op.execute("ALTER TABLE documents ADD COLUMN embedding_model text NULL")
    op.execute("ALTER TABLE documents ADD COLUMN chunking_version text NULL")
    op.execute(
        """
        UPDATE documents
        SET embedding_model = 'text-embedding-3-small', chunking_version = 'v1'
        WHERE status = 'embedded' AND embedding_model IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS chunking_version")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding_model")
