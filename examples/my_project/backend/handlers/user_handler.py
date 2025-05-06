# my_project/backend/handlers/user_handler.py
from backend.db_utils import get_connection # type: ignore


def handle_user_request(data: dict):
    """
    Insert or update a user record.
    """
    name = data.get("name")
    email = data.get("email")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
        )
        conn.commit()
        user_id = cur.lastrowid
    return {"id": user_id, "name": name, "email": email}
