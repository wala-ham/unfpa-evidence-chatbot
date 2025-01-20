import streamlit as st
from speech_to_text import record_audio  # Importer la fonction depuis speech_to_text
from retrieval_agent import retrieve_chunks
from response_agent import generate_response
from visualization_agent import needs_graphic, generate_graphic

# --- Streamlit Interface ---
st.title("Chat with Gemini")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create columns for the interface
col1, col2 = st.columns([6, 1])

# Add a placeholder for the recording indicator
recording_placeholder = st.empty()

# User input section (text or microphone)
with col1:
    query = st.chat_input("Posez une question ici...")

# Microphone button to trigger Google Cloud Speech-to-Text
with col2:
    if st.button("🎤"):
        recording_placeholder.markdown("### Enregistrement en cours... 🎤")
        query = record_audio()  # Capture audio using Google Cloud Speech
        recording_placeholder.empty()  # Clear the message after recording

# If the user submits a query
if query:
    # Add user query to the session state messages
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Retrieve relevant documents (chunks)
    chunks = retrieve_chunks(query)
    combined_input = " ".join([chunk["chunk"] for chunk in chunks]) if chunks else query

    # Generate a response using the model
    response = generate_response(query, combined_input)
    
    # Display the model's response
    with st.chat_message("assistant"):
        st.markdown(response)

        # Check if a graphic is needed
        if needs_graphic(query, response):
            st.write("Un graphique est nécessaire. Génération en cours...")
            code_snippet = generate_graphic(query, response)
            if code_snippet:
                st.write("Code Python généré pour le graphique :")
                st.code(code_snippet, language="python")
                st.image("generated_graph.png", caption="Graphique généré")
            else:
                st.error("Échec de la génération du graphique.")
        else:
            st.write("Pas de graphique nécessaire pour cette réponse.")

    # Add model's response to the session state messages
    st.session_state.messages.append({"role": "assistant", "content": response})

