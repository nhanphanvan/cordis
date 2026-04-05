from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import DatabaseModel


class RepositoryMember(DatabaseModel):
    __tablename__ = "repository_members"
    __table_args__ = (UniqueConstraint("repository_id", "user_id", name="uq_repository_members_repository_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)

    repository = relationship("Repository", back_populates="members")
    user = relationship("User", back_populates="repository_memberships")
    role = relationship("Role", back_populates="repository_memberships")
