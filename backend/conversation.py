from firebase_admin import firestore, credentials, initialize_app
import datetime
from firebase_admin import firestore

def update_message_feedback(db, user_name, conversation_id, message_index, feedback_data):
    """Updates the feedback of a specific message in Firestore."""
    try:
        print(
            f"Updating feedback for user: {user_name}, conversation_id: {conversation_id}, message_index: {message_index}"
        )
        messages_result = get_messages(db, user_name, conversation_id)

        if messages_result and "messages" in messages_result:
            messages = messages_result["messages"]

            if 0 <= message_index < len(messages):
                # Instead of getting a message_id, we'll update based on index
                # Make sure your 'get_messages' function returns messages in the correct order
                message_ref = (
                    db.collection("users")
                    .document(user_name)
                    .collection("conversations")
                    .document(conversation_id)
                    .collection("messages")
                    .order_by("timestamp")  # Assuming you have a timestamp field
                    .get()[message_index]
                    .reference
                )  # Get the reference of the message by index

                message_ref.update(feedback_data)  # Update only the feedback field

                print(f"Feedback updated successfully for message index: {message_index}")
                return True
            else:
                print("Invalid message index.")
        else:
            print("Error getting messages or no messages found.")

    except Exception as e:
        print(f"An error occurred: {e}")

    return False

def save_message(db, user_id, conversation_id, message_data):
    try:
        messages_ref = db.collection(f"users/{user_id}/conversations/{conversation_id}/messages")
        message_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        message_ref = messages_ref.add(message_data)
        return {"message_id": message_ref[1].id, "message_data": message_data}
    except Exception as e:
        return {"error": str(e)}

def get_conversations(db, user_id):
    try:
        conversations_ref = db.collection(f"users/{user_id}/conversations")
        conversations = []
        for doc in conversations_ref.stream():
            conversation = doc.to_dict()
            conversation["conversation_id"] = doc.id
            # conversation['created_at'] = conversation['created_at'].strftime('%Y-%m-%d %H:%M')  # This is converting it to a string
            conversations.append(conversation)
        return {"conversations": conversations}
    except Exception as e:
        return {"error": str(e)}

def get_messages(db, user_id, conversation_id):
    try:
        messages_ref = db.collection(f"users/{user_id}/conversations/{conversation_id}/messages")
        messages = []
        for doc in messages_ref.stream():
            msg = doc.to_dict()
            msg["message_id"] = doc.id
            messages.append(msg)
        return {"messages": messages}
    except Exception as e:
        return {"error": str(e)}

def create_conversation(db, user_id, conversation_data):
    try:
        conversations_ref = db.collection(f"users/{user_id}/conversations")
        conversation_data["created_at"] = datetime.datetime.now(datetime.timezone.utc)
        conversation_ref = conversations_ref.add(conversation_data)
        return {"conversation_id": conversation_ref[1].id, "conversation_data": conversation_data}
    except Exception as e:
        return {"error": str(e)}

def delete_conversation(db, user_id, conversation_id):
    try:
        conversation_ref = db.collection(f"users/{user_id}/conversations/{conversation_id}")
        conversation_ref.delete()
        return {"message": f"Conversation {conversation_id} deleted successfully."}
    except Exception as e:
        return {"error": str(e)}

def delete_message(db, user_id, conversation_id, message_id):
    try:
        message_ref = db.collection(f"users/{user_id}/conversations/{conversation_id}/messages/{message_id}")
        message_ref.delete()
        return {"message": f"Message {message_id} deleted successfully."}
    except Exception as e:
        return {"error": str(e)}
