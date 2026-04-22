from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CustomerModel(Base):
    __tablename__ = "customers"

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
