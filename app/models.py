from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, DateTime, Integer, String, Boolean, func

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    tg_user_id: Mapped[int] = mapped_column(Integer, index=True)
    tg_chat_id: Mapped[int] = mapped_column(Integer, index=True)

    source: Mapped[str] = mapped_column(String(20))  # text | voice
    raw_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(50), default="unknown")
    topic: Mapped[str] = mapped_column(String(80), default="unknown")
    urgency: Mapped[str] = mapped_column(String(20), default="low")  # low|medium|high
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")  # negative|neutral|positive

    delegate_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    automate_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    hire_candidate: Mapped[bool] = mapped_column(Boolean, default=False)

    summary: Mapped[str] = mapped_column(Text, default="")
