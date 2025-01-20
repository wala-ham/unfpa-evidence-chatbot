import streamlit as st
from retrieval_agent import retrieve_chunks
from response_agent import generate_response
from visualization_agent import needs_graphic, generate_graphic

# Streamlit App Configuration
st.set_page_config(
    page_title="AI Orchestrator",
    page_icon="🤖",
    layout="wide"
)

# Conversation History and Session State for Storing Chats
if 'conversations' not in st.session_state:
    st.session_state['conversations'] = []
if 'active_conversation' not in st.session_state:
    st.session_state['active_conversation'] = None
if 'current_status' not in st.session_state:
    st.session_state['current_status'] = {'query': '', 'response': '', 'graphic_needed': False}

# App Title
st.title("AI-Powered Orchestrator")
st.subheader("Integrated Retriever, Generator, and Visualization")

# Sidebar: History of Conversations
st.sidebar.header("Conversation History")
conversation_titles = [chat['title'] for chat in st.session_state['conversations']]
selected_convo = st.sidebar.selectbox(
    "Select a Previous Chat or Start a New One",
    ["New Chat"] + conversation_titles
)

# Handle Chat Selection
if selected_convo == "New Chat":
    st.session_state['active_conversation'] = None
else:
    st.session_state['active_conversation'] = next(
        chat for chat in st.session_state['conversations'] if chat['title'] == selected_convo
    )

# Main Content Area
if st.session_state['active_conversation']:
    # Display the selected conversation
    convo = st.session_state['active_conversation']
    st.write(f"### Conversation: {convo['title']}")
    for i, item in enumerate(convo['chat_history']):
        st.write(f"**{item['role']}:** {item['message']}")

# Query Input (Bottom of the screen)
st.markdown("### Ask a New Query")
user_query = st.text_area("Type your query", placeholder="Type a question or command...", key="query_input", height=100)

# Automatically trigger on Enter key press
if user_query:
    # Validate the input
    if not user_query.strip():
        st.error("Please enter a valid query.")
    else:
        # Step 1: Retrieve Chunks
        with st.spinner('Retrieving relevant chunks...'):
            chunks = retrieve_chunks(user_query)
        
        if chunks:
            st.write("### Retrieved Chunks:")
            for i, chunk in enumerate(chunks):
                st.write(f"**Chunk {i+1}:** {chunk['chunk']}")
                st.write(f"**Source:** {chunk['source']}")
        else:
            st.warning("No relevant chunks found.")

        # Combine Chunks for Input
        combined_input = "\n".join([chunk['chunk'] for chunk in chunks])

        # Step 2: Generate Response
        st.write("### Generating Response...")
        if combined_input:
            try:
                response = generate_response(user_query, combined_input)
                st.write("### Generated Response:")
                st.write(response)

                # Step 3: Determine if a Graphic is Needed
                st.write("### Checking for Graphic Requirement...")
                if needs_graphic(user_query, response):
                    st.write("A graphic is required. Generating...")
                    with st.spinner('Generating graphic...'):
                        code_snippet = generate_graphic(user_query, response)
                        if code_snippet:
                            st.write("Generated Python Code for the Graphic:")
                            st.code(code_snippet, language="python")
                            st.image("generated_graph.png", caption="Generated Graphic")
                        else:
                            st.error("Failed to generate a graphic.")
                else:
                    st.write("No graphic is needed for this response.")

                # Save the conversation (Title and query/response)
                conversation_title = f"Conversation {len(st.session_state['conversations']) + 1}"
                new_conversation = {
                    'title': conversation_title,
                    'query': user_query,
                    'response': response,
                    'chat_history': [{'role': 'User', 'message': user_query}, {'role': 'AI', 'message': response}]
                }
                st.session_state['conversations'].append(new_conversation)
                st.session_state['active_conversation'] = new_conversation
                st.session_state.current_status = {'query': '', 'response': '', 'graphic_needed': False}

                # Reset the query input field here
                st.session_state.query_input = ""  # Reset the value but don't modify the widget

            except Exception as e:
                st.error(f"An error occurred while generating the response: {e}")
        else:
            st.warning("No content to generate a response from.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Developed with ❤️ using Streamlit.")
