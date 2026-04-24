from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

MYSQL_CHARSET = "utf8mb4"
MYSQL_COLLATION = "utf8mb4_0900_ai_ci"


class Base(DeclarativeBase):
    pass


class CustomerModel(Base):
    __tablename__ = "customers"
    __table_args__ = {
        "mysql_charset": MYSQL_CHARSET,
        "mysql_collate": MYSQL_COLLATION,
    }

    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
