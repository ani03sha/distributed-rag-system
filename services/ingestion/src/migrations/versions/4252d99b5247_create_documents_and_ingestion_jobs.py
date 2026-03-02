"""create_documents_and_ingestion_jobs

Revision ID: 4252d99b5247
Revises:
Create Date: 2026-03-02 07:36:52.796987

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4252d99b5247"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.VARCHAR(50), nullable=False),
        sa.Column("external_id", sa.VARCHAR(500), unique=True),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("url", sa.TEXT(), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("chunk_count", sa.INTEGER),
        sa.Column("index_version", sa.VARCHAR(50)),
        sa.Column("status", sa.VARCHAR(20), server_default="pending"),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
        ),
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trigger", sa.VARCHAR(20), nullable=False),
        sa.Column("source", sa.VARCHAR(50), nullable=False),
        sa.Column("status", sa.VARCHAR(20), server_default="queued"),
        sa.Column("docs_total", sa.INTEGER()),
        sa.Column("docs_indexed", sa.INTEGER(), server_default="0"),
        sa.Column("docs_failed", sa.INTEGER(), server_default="0"),
        sa.Column("error", sa.TEXT()),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
        ),
    )


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
