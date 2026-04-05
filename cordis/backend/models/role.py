from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class Role(TimestampedModel):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    repository_memberships = relationship("RepositoryMember", back_populates="role")
