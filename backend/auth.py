import firebase_admin
from firebase_admin import auth, credentials
import os
import requests

def initialize_firebase():
    if not firebase_admin._apps:  # Check if already initialized
      firebase_admin.initialize_app()
# Initialize Firebase
# def initialize_firebase():
#     """
#     Initialise Firebase with the service account key.
#     """
#     if not firebase_admin._apps:
#         cred = credentials.Certificate(r"C:\Users\WalaHammemi\OneDrive - Naxxum\Bureau\Optimisation\Agents\service-account-key.json")
#         firebase_admin.initialize_app(cred)

# User Signup
def sign_up_user(email, password):
    """
    Create a new user with the provided email and password.
    Args:
        email (str): The user's email address.
        password (str): The user's password.
    Returns:
        dict: User details if successful, None if the email is already registered.
    """
    try:
        # Check if the email is already registered
        auth.get_user_by_email(email)
        return {"error": "User already exists"}
    except auth.UserNotFoundError:
        # Email doesn't exist, so we can create the user
        try:
            user = auth.create_user(email=email, password=password)
            return {"uid": user.uid, "email": user.email}
        except Exception as e:
            return {"error": str(e)}

# Verify User Token
def authenticate_user(id_token):
    """
    Verify the Firebase ID token.
    Args:
        id_token (str): Firebase ID token.
    Returns:
        dict: Decoded token if valid, error details otherwise.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {"uid": decoded_token["uid"], "email": decoded_token["email"]}
    except Exception as e:
        return {"error": str(e)}

# Sign In with Email and Password
def sign_in_with_email_and_password(email, password):
    """
    Sign in a user with email and password using Firebase Authentication.
    Args:
        email (str): The user's email address.
        password (str): The user's password.
    Returns:
        str: The ID token if successful, None otherwise.
    """
    api_key = os.getenv("FIREBASE_API_KEY", "AIzaSyAFjqeABerwL1fKQv_PWXPzItvQtVWPPEo")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    try:
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            return {"idToken": data['idToken'], "refreshToken": data['refreshToken']}
        else:
            error = response.json()
            return {"error": error.get('error', {}).get('message', 'Unknown error')}
    except requests.RequestException as e:
        return {"error": str(e)}

# Delete User
def delete_user(uid):
    """
    Delete a user by UID.
    Args:
        uid (str): The user's UID.
    Returns:
        dict: Success message or error details.
    """
    try:
        auth.delete_user(uid)
        return {"message": f"User {uid} deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

# Get All Users
def get_all_users():
    """
    Retrieve all registered users in Firebase Authentication.
    Returns:
        list: List of user records or an error message.
    """
    try:
        users = []
        page = auth.list_users()
        while page:
            for user in page.users:
                users.append({"uid": user.uid, "email": user.email})
            page = page.get_next_page()
        return users
    except Exception as e:
        return {"error": str(e)}


