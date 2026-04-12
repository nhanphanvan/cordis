"""replace repository public flag with visibility and object exposure

Revision ID: 20260412_000001
Revises:
Create Date: 2026-04-12 12:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260412_000001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("visibility", sa.String(length=32), nullable=True))
    op.add_column("repositories", sa.Column("allow_public_object_urls", sa.Boolean(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE repositories
            SET visibility = CASE
                WHEN is_public THEN 'authenticated'
                ELSE 'private'
            END
            """
        )
    )
    op.execute(sa.text("UPDATE repositories SET allow_public_object_urls = false"))

    op.alter_column("repositories", "visibility", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("repositories", "allow_public_object_urls", existing_type=sa.Boolean(), nullable=False)
    op.drop_column("repositories", "is_public")


def downgrade() -> None:
    op.add_column("repositories", sa.Column("is_public", sa.Boolean(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE repositories
            SET is_public = CASE
                WHEN visibility = 'authenticated' THEN true
                ELSE false
            END
            """
        )
    )

    op.alter_column("repositories", "is_public", existing_type=sa.Boolean(), nullable=False)
    op.drop_column("repositories", "allow_public_object_urls")
    op.drop_column("repositories", "visibility")
