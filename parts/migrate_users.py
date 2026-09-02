# migrate_users.py — run once, then delete
from models import get_session, get_users_session, Users
from sqlalchemy import create_engine, text

src_engine = create_engine("sqlite:///app_data.db")

with src_engine.connect() as conn:
    rows = conn.execute(
        text("SELECT user_name, password_hash, is_admin, is_active " "FROM users")
    ).fetchall()

with get_users_session() as session:
    for row in rows:
        if session.query(Users).filter_by(user_name=row[0]).first():
            continue  # Skip if already exists
        new_user = Users(
            user_name=row[0],
            password_hash=row[1],
            is_admin=bool(row[2]),
            is_active=bool(row[3]),
        )
        session.add(new_user)

print(f"Migrated {len(rows)} user(s) to users.db")
