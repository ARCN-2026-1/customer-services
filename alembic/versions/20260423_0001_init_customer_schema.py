"""init customer schema

Revision ID: 20260423_0001
Revises:
Create Date: 2026-04-23 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None

MYSQL_CHARSET = "utf8mb4"
MYSQL_COLLATION = "utf8mb4_0900_ai_ci"


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("customer_id"),
        mysql_charset=MYSQL_CHARSET,
        mysql_collate=MYSQL_COLLATION,
    )
    op.create_index(
        op.f("ix_customers_email"),
        "customers",
        ["email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_table("customers")
