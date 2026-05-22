from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Account, HistoryChat

DATABASE_URL = "sqlite:///chat_app.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_account_list():
    db = SessionLocal()
    try:
        accounts = db.query(Account).all()

        return [
            {
                "id": account.id,
                "name": account.name,
            }
            for account in accounts
        ]
    finally:
        db.close()


def get_history_list_by_account_id(account_id: int):
    db = SessionLocal()

    try:
        chats = (
            db.query(HistoryChat)
            .filter(HistoryChat.user_id == account_id)
            .all()
        )

        return [
            {
                "id": chat.id,
                "title": chat.title,
                "content": chat.content,
                "user_id": chat.user_id,
            }
            for chat in chats
        ]

    finally:
        db.close()


def create_account(name: str):
    db = SessionLocal()

    try:
        account = Account(name=name)

        db.add(account)
        db.commit()
        db.refresh(account)

        return {
            "id": account.id,
            "name": account.name,
        }

    finally:
        db.close()


def create_history_chat(
    title: str,
    content: str,
    user_id: int,
):
    db = SessionLocal()

    try:
        account = (
            db.query(Account)
            .filter(Account.id == user_id)
            .first()
        )

        if not account:
            raise ValueError(
                f"Account with id={user_id} was not found"
            )

        chat = HistoryChat(
            title=title,
            content=content,
            user_id=user_id,
        )

        db.add(chat)
        db.commit()
        db.refresh(chat)

        return {
            "id": chat.id,
            "title": chat.title,
            "content": chat.content,
            "user_id": chat.user_id,
        }

    finally:
        db.close()


def update_history_chat(
    chat_id: int,
    title: str | None = None,
    content: str | None = None,
):
    db = SessionLocal()

    try:
        chat = (
            db.query(HistoryChat)
            .filter(HistoryChat.id == chat_id)
            .first()
        )

        if not chat:
            raise ValueError(
                f"History chat with id={chat_id} was not found"
            )

        if title is not None:
            chat.title = title

        if content is not None:
            chat.content = content

        db.commit()
        db.refresh(chat)

        return {
            "id": chat.id,
            "title": chat.title,
            "content": chat.content,
            "user_id": chat.user_id,
        }

    finally:
        db.close()
        
def reset_all_data():
    db = SessionLocal()

    try:
        db.query(HistoryChat).delete()
        db.query(Account).delete()

        db.commit()

        return {
            "message": "All account and history chat data has been reset"
        }

    finally:
        db.close()