from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cordis.backend.models.base import TimestampedModel


class UploadSessionPart(TimestampedModel):
    __tablename__ = "upload_session_parts"
    __table_args__ = (UniqueConstraint("session_id", "part_number", name="uq_upload_session_parts_session_part"),)

    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False)
    part_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    etag: Mapped[str] = mapped_column(String(255), nullable=False)

    session = relationship("UploadSession")
