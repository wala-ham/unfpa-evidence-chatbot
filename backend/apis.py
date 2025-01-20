from flask import Flask, request, jsonify
from conversation import (
    save_message, 
    get_conversations, 
    get_messages, 
    create_conversation, 
    delete_conversation, 
    delete_message
)
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from firebase_admin import firestore

# Initialize Firestore client
db = firestore.client()

app = Flask(__name__)

# User Registration
@app.route("/auth/register", methods=["POST"])
def register_user():
    """
    Registers a new user with email and password.

    Request JSON:
    {
        "email": "example@mail.com",
        "password": "securepassword"
    }
    """
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user_id = str(uuid.uuid4())
        hashed_password = generate_password_hash(password)

        # Save user to Firestore
        db.collection("users").document(user_id).set({
            "email": email,
            "password": hashed_password,
        })

        return jsonify({"message": "User registered successfully", "user_id": user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# User Login
@app.route("/auth/login", methods=["POST"])
def login_user():
    """
    Logs in a user with email and password.

    Request JSON:
    {
        "email": "example@mail.com",
        "password": "securepassword"
    }
    """
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Fetch user from Firestore
        users_ref = db.collection("users")
        user_query = users_ref.where("email", "==", email).get()

        if not user_query:
            return jsonify({"error": "Invalid credentials"}), 401

        user_doc = user_query[0]
        user_data = user_doc.to_dict()

        # Validate password
        if not check_password_hash(user_data["password"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({"message": "Login successful", "user_id": user_doc.id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all conversations for a user
@app.route("/users/<user_id>/conversations", methods=["GET"])
def api_get_conversations(user_id):
    return jsonify(get_conversations(user_id))

# Create a new conversation
@app.route("/users/<user_id>/conversations", methods=["POST"])
def api_create_conversation(user_id):
    data = request.json
    return jsonify(create_conversation(user_id, data))

# Get all messages in a conversation
@app.route("/users/<user_id>/conversations/<conversation_id>/messages", methods=["GET"])
def api_get_messages(user_id, conversation_id):
    return jsonify(get_messages(user_id, conversation_id))

# Save a message in a conversation
@app.route("/users/<user_id>/conversations/<conversation_id>/messages", methods=["POST"])
def api_save_message(user_id, conversation_id):
    data = request.json
    return jsonify(save_message(user_id, conversation_id, data))

# Delete a conversation
@app.route("/users/<user_id>/conversations/<conversation_id>", methods=["DELETE"])
def api_delete_conversation(user_id, conversation_id):
    return jsonify(delete_conversation(user_id, conversation_id))

# Delete a message in a conversation
@app.route("/users/<user_id>/conversations/<conversation_id>/messages/<message_id>", methods=["DELETE"])
def api_delete_message(user_id, conversation_id, message_id):
    return jsonify(delete_message(user_id, conversation_id, message_id))

if __name__ == "__main__":
    app.run(debug=True)
