import os
import re
from collections import deque
import streamlit as st
from datetime import datetime, timezone

# Custom modules
from retrieval_agent import retrieve_chunks
from response_agent import generate_response
from visualization_agent import needs_graphic, generate_graphic
from storage_utils import upload_to_storage, sanitize_filename

# Import functions from backend modules
from backend.auth import sign_up_user, authenticate_user, sign_in_with_email_and_password, delete_user, get_all_users, initialize_firebase
from backend.conversation import save_message, get_conversations, get_messages, create_conversation, delete_conversation, delete_message

# Firebase imports
from firebase_admin import firestore
from streamlit.runtime.caching import cache_data

# Initialize Firebase
initialize_firebase()
db = firestore.client()

# --- Constants ---
STATIC_IMG_DIR = "static_img"
os.makedirs(STATIC_IMG_DIR, exist_ok=True)

# --- Page Configuration ---
st.set_page_config(page_title="Chat App with Authentication", page_icon="🤖", layout="wide")

# --- Session State ---
if "page" not in st.session_state:
    st.session_state.page = "guest"
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "id_token" not in st.session_state:
    st.session_state.id_token = None
if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = None  # Currently selected conversation
if "messages" not in st.session_state:
    st.session_state.messages = deque(maxlen=5)
if "conversation_titles" not in st.session_state:
    st.session_state.conversation_titles = {}  # Store conversation titles

# --- Helper Functions ---

def load_conversation(conversation_id):
    """Loads the messages for the selected conversation."""
    st.session_state.current_conversation = conversation_id
    st.session_state.messages = deque(maxlen=5)  # Clear current messages

    messages_result = get_messages(db, st.session_state.user_name, conversation_id)
    if messages_result and "messages" in messages_result:
        for msg in messages_result["messages"]:
            # Correctly determine the role (user or assistant)
            if "query" in msg:
                st.session_state.messages.append({"role": "user", "content": msg["query"]})
            if "response" in msg:
                st.session_state.messages.append({"role": "assistant", "content": msg["response"]})

def new_conversation():
    """Starts a new conversation."""
    st.session_state.current_conversation = None
    st.session_state.messages = deque(maxlen=5)  # Clear current messages

    # --- Create a new conversation in Firestore ---
    if st.session_state.user_authenticated:
        user_ref = db.collection('users').document(st.session_state.user_name)
        conversation_data = {
            "created_at": datetime.now(timezone.utc),
            "title": ""  # Placeholder for title, will be updated later
        }
        create_conversation_result = create_conversation(db, st.session_state.user_name, conversation_data)

        if create_conversation_result and "conversation_id" in create_conversation_result:
            conversation_id = create_conversation_result["conversation_id"]
            st.session_state.current_conversation = conversation_id
        else:
            st.error("Failed to create a new conversation.")

def get_conversation_title(conversation_id):
    """Gets the title of a conversation from session state or Firestore."""
    if conversation_id in st.session_state.conversation_titles:
        return st.session_state.conversation_titles[conversation_id]

    # Fetch from Firestore if not in session state
    user_ref = db.collection('users').document(st.session_state.user_name)
    conversation_ref = user_ref.collection('conversations').document(conversation_id)
    conversation = conversation_ref.get()
    if conversation.exists:
        title = conversation.to_dict().get("title", "Conversation")
        st.session_state.conversation_titles[conversation_id] = title  # Cache in session state
        return title
    else:
        return "Conversation"

def set_conversation_title(conversation_id, title):
    """Sets the title of a conversation (in session state and Firestore)."""
    st.session_state.conversation_titles[conversation_id] = title

    # Update title in Firestore
    if st.session_state.user_authenticated:
        user_ref = db.collection('users').document(st.session_state.user_name)
        conversation_ref = user_ref.collection('conversations').document(conversation_id)
        conversation_ref.update({"title": title})

# --- Sidebar ---
with st.sidebar:
    st.title("Navigation")

    if st.session_state.user_authenticated:
        # --- Display previous conversations (sorted by creation time, newest first) ---
        # --- Button to create a new conversation ---
        if st.button("New Conversation"):
            new_conversation()

        # --- Display previous conversations (sorted by creation time, newest first) ---  
        st.subheader("Conversations")
        conversations_result = get_conversations(db, st.session_state.user_name)

        if conversations_result and "conversations" in conversations_result:
            conversations = conversations_result["conversations"]

            # Sort conversations by 'created_at' in descending order (newest first)
            conversations.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

            for conv_data in conversations:
                conversation_id = conv_data.get('conversation_id', None)
                if conversation_id:
                    # Get conversation title
                    title = get_conversation_title(conversation_id)

                    # Button for each conversation
                    if st.button(title, key=f"conv_{conversation_id}"):
                        load_conversation(conversation_id)
                else:
                    st.write("Error: Could not find conversation ID.")

        elif conversations_result and "error" in conversations_result:
            st.error(f"Error getting conversations: {conversations_result['error']}")
        else:
            st.write("No conversations found.")

        # # --- Button to create a new conversation ---
        # if st.button("New Conversation"):
        #     new_conversation()

# --- Top Bar ---
# Create two columns for the top bar
col1, col2, col3 = st.columns([3, 1, 2])  # Adjust the ratio as needed

# Column 1: Title
with col1:
    st.title("UNFPA-Chatbot")

# Column 3: Authentication Buttons (aligned to the right)
with col3:
    if st.session_state.user_authenticated:
        # Display welcome message aligned to the right
        st.write(f"👤 Welcome, {st.session_state.user_name}!")
    # Use a placeholder for buttons to keep them side by side
    auth_buttons_placeholder = st.empty()
    with auth_buttons_placeholder.container():
        if st.session_state.user_authenticated:
            # Logout button
            if st.button("Logout", key="logout_btn"):
                st.session_state.update(
                    user_authenticated=False,
                    page="guest",
                    user_name=None,
                    id_token=None
                )
                new_conversation()  # Start a new conversation on logout
                st.rerun()
        else:
            col_login, col_signup = st.columns(2)
            # Login button
            with col_login:
                if st.button("Login", key="login_btn"):
                    st.session_state.page = "authentication"
                    st.rerun()
            # Sign Up button
            with col_signup:
                if st.button("Sign Up", key="signup_btn"):
                    st.session_state.page = "authentication"
                    st.rerun()

# --- Main Page Logic ---
if st.session_state.page == "guest":
    st.write("You are currently in **Guest Mode**. Log in or sign up for a personalized experience.")

    # Chat for guest users
    st.subheader("Chatbot")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    query = st.chat_input("Ask a question...")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Prepare context
        chunks = retrieve_chunks(query)
        # Combine Chunks for Input
        combined_input = "\n".join([chunk['chunk'] for chunk in chunks])
       
        response = generate_response(query, combined_input)
        # st.write("### Generated Response:")
        # st.write(response)

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

elif st.session_state.page == "authentication":
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:  # --- Login Tab ---
        st.subheader("Log In")
        with st.form(key="login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button(label="Log In")

            if submit_login:
                if email and password:
                    # Sign in the user
                    login_result = sign_in_with_email_and_password(email, password)
                    if "idToken" in login_result:
                        id_token = login_result["idToken"]

                        # Verify the ID token
                        auth_result = authenticate_user(id_token)
                        if "uid" in auth_result:
                            st.session_state.user_authenticated = True
                            st.session_state.user_name = email.split('@')[0]  # Extract username
                            st.session_state.page = "chat"
                            st.session_state.id_token = id_token
                            new_conversation()  # Start a new conversation on login
                            st.success(f"Welcome back, {st.session_state.user_name}!")
                            st.rerun()  # Rerun the app to update the page
                        else:
                            st.error(f"Authentication failed: {auth_result.get('error', 'Unknown error')}")
                    else:
                        st.error(f"Login failed: {login_result.get('error', 'Unknown error')}")
                else:
                    st.error("Both fields are required.")

    with tab2:  # --- Sign Up Tab ---
        st.subheader("Sign Up")
        with st.form(key="signup_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit_signup = st.form_submit_button(label="Sign Up")

            if submit_signup:
                if email and password:
                    signup_result = sign_up_user(email, password)
                    if "uid" in signup_result:
                        st.session_state.user_authenticated = True
                        st.session_state.user_name = email.split('@')[0]
                        st.session_state.page = "chat"
                        new_conversation()
                        st.success(f"Welcome, {st.session_state.user_name}! You can now log in.")
                        st.rerun()
                    else:
                        st.error(f"Error creating user: {signup_result.get('error', 'Unknown error')}")
                else:
                    st.error("Both fields are required.")

elif st.session_state.page == "chat" and st.session_state.user_authenticated:
    st.subheader("UNFPA Assistant")

    # Display messages for the selected conversation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    query = st.chat_input("Ask something...")
    if query:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Retrieve relevant documents (chunks)
        chunks = retrieve_chunks(query)
        # Combine Chunks for Input
        combined_input = "\n".join([chunk['chunk'] for chunk in chunks])

        response = generate_response(query, combined_input)

        # Add assistant message to chat
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Check if a graphic is needed
        if needs_graphic(query, response):
            st.write("A graphic is required. Generating...")
            code_snippet = generate_graphic(query, response)

            if code_snippet:
                sanitized_query = sanitize_filename(query)
                graphic_filename = f"{sanitized_query}_generated_graph.png"
                graphic_path = os.path.join(STATIC_IMG_DIR, graphic_filename)
                code_snippet += f"\nplt.savefig('{graphic_path}')"

                try:
                    exec_globals = {"__name__": "__main__"}
                    exec_locals = {}
                    exec(code_snippet, exec_globals, exec_locals)

                    st.image(graphic_path, caption="Generated Graphic")
                    st.write(f"Graphic saved locally at: {graphic_path}")

                    # Upload to GCS
                    bucket_name = 'unfpa-444213.appspot.com'
                    gcs_destination = f"images/{graphic_filename}"

                    if upload_to_storage(bucket_name, graphic_path, gcs_destination):
                        st.write(f"Graphic successfully uploaded to GCS at: {gcs_destination}")
                        graphic_url = f"https://storage.googleapis.com/{bucket_name}/{gcs_destination}"

                    else:
                        st.error("Failed to upload the graphic to GCS.")

                except Exception as e:
                    st.error(f"Failed to generate the graphic: {e}")

        # Save message to the currently selected conversation
        if st.session_state.current_conversation:
            message_data = {
                'timestamp': datetime.now(timezone.utc),
                'query': query,
                'response': response,
            }
            if 'graphic_url' in locals():
                message_data['graphic_url'] = graphic_url

            save_message(db, st.session_state.user_name, st.session_state.current_conversation, message_data)

            # Update conversation title based on the first query
            conversation_ref = db.collection('users').document(st.session_state.user_name).collection('conversations').document(st.session_state.current_conversation)
            conversation = conversation_ref.get()
            if conversation.exists:
                current_title = conversation.to_dict().get("title", "")
                if not current_title:
                    # Use the first query as the title (up to 50 characters)
                    new_title = query[:50]
                    if len(query) > 50:
                        new_title += "..."  # Indicate that the title is truncated
                    set_conversation_title(st.session_state.current_conversation, new_title)
        else:
            st.error("No conversation selected.")




# gcloud run deploy evidence-assistant-chatbot `
# >>   --source . `
# >>   --region us-central1 `
# >>   --service-account vertex-ai-ntegration-second@unfpa-444213.iam.gserviceaccount.com