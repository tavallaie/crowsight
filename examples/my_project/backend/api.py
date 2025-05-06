# my_project/backend/api.py
from flask import Flask, request, jsonify  # type: ignore
from .db_utils import get_user_by_id  # type: ignore
from backend.handlers.user_handler import handle_user_request  # type: ignore

app = Flask(__name__)


@app.route("/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route("/user", methods=["POST"])
def create_user():
    data = request.json
    result = handle_user_request(data)
    return jsonify(result), 201


if __name__ == "__main__":
    app.run(debug=True)
