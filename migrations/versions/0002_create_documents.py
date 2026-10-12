"""create document and chunk tables

Revision ID: 0002_create_documents
Revises: 0001_enable_pgvector
Create Date: 2026-10-12

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_create_documents"
down_revision: str | None = "0001_enable_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store documents and nullable vectors. The dimension matches text-embedding-3-small.

    Changing the embedding model requires a new migration. The column is not inferred
    from configuration.
    """

    op.execute(
        """
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            filename text NOT NULL,
            media_type text NOT NULL,
            content_sha256 text NOT NULL UNIQUE,
            byte_size integer NOT NULL CHECK (byte_size >= 0),
            status text NOT NULL,
            failure_detail text NULL,
            chunk_count integer NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
            created_at timestamptz NOT NULL,
            updated_at timestamptz NOT NULL,
            CONSTRAINT documents_content_sha256_length CHECK (char_length(content_sha256) = 64)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE document_chunks (
            document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            position integer NOT NULL CHECK (position >= 0),
            content text NOT NULL,
            embedding vector(1536),
            PRIMARY KEY (document_id, position)
        )
        """
    )


def downgrade() -> None:
    """Remove ingestion tables. The vector extension stays until its own migration."""

    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS documents")
