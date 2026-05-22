from sqlalchemy import create_engine, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

class Base(DeclarativeBase):
    pass

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    history_chats: Mapped[list["HistoryChat"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    def __repr__(self):
        return f"Account(id={self.id}, name='{self.name}')"

class HistoryChat(Base):
    __tablename__ = "history_chats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False
    )
    user: Mapped["Account"] = relationship(back_populates="history_chats")
    def __repr__(self):
        return (
            f"HistoryChat(id={self.id}, "
            f"title='{self.title}', "
            f"user_id={self.user_id})"
        )