from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UsageMonthly(Base):
    __tablename__ = "usage_monthly"
    __table_args__ = (UniqueConstraint("user_id", "usage_month", name="uq_usage_monthly_user_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    usage_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    image_generation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="monthly_usage")
