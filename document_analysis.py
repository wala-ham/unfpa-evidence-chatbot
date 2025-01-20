import streamlit as st
from vertexai import generative_models
from vertexai.generative_models import GenerationConfig, GenerativeModel
import PyPDF2
from docx import Document
import io
import pandas as pd
from google.cloud import aiplatform
import os
from google.oauth2 import service_account
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold

# Configure your API key
genai.configure(api_key="AIzaSyAAYCX3p58fp_9Z4FVlp1JQ5G0Vd2KXxZA")  # Replace with your actual API key

# Default generation configuration
generation_config = {
    "max_output_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
}

# Safety settings for harmful content filtering
safety_settings = {
    "HARM_CATEGORY_HATE_SPEECH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "HARM_CATEGORY_DANGEROUS_CONTENT": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "HARM_CATEGORY_HARASSMENT": HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# Initialize the model globally (singleton)
model = genai.GenerativeModel(
    "gemini-2.0-flash-exp",  # Use a valid model name like "gemini-pro"
    system_instruction=[
        "You are a helpful, knowledgeable, and human-like assistant.",
        "Generate a clear, concise, and fluent response in natural language based on the query and relevant chunks.",
        "Ensure the response is coherent, well-structured, and easy to understand.",
        "You are a helpful assistant, you will provide responses that are as detailed as possible"
    ],
    generation_config=generation_config,
    safety_settings=safety_settings,
)


def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# --- Fonction d'analyse ---

def analyze_document(text):
    prompt = f"""
    **Comprehensive analytical synthesis:**
    Generate a synthesis of the provided document, which appears to be an evaluation report.
    Organize the output in a table format with the following columns:

    | Theme | Trend | Pattern | Organizational Learning Need | Good Practice | Lesson Learned | Reference |
    |---|---|---|---|---|---|---|

    Populate each cell of the table with relevant information extracted from the document. 
    If a particular category is not applicable or no information is found, leave the cell blank.
    Provide references to specific sections or pages in the document where possible.

    **Document:**
    {text}
    """
    response = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    return response.text

# --- Fonction pour convertir le texte en tableau ---

def text_to_table(text):
    """
    Convertit la réponse en format de table en un DataFrame pandas.
    """
    try:
        # Diviser le texte en lignes et ignorer les lignes de séparation de tableau
        lines = [line.strip() for line in text.split('\n') if line.strip() and '|' in line]
        
        # Extraire les en-têtes et les données
        headers = [header.strip() for header in lines[0].split('|') if header.strip()]
        data_rows = [line.split('|')[1:-1] for line in lines[2:]]  # Ignorer la première ligne (en-têtes) et la ligne de tirets

        # Créer un DataFrame pandas
        df = pd.DataFrame(data_rows, columns=headers)
        return df
    except Exception as e:
        st.error(f"Erreur lors de la conversion du texte en tableau : {e}")
        return pd.DataFrame()
    
# --- Interface Streamlit ---

st.title("Evaluation Report Analyzer")

# Initialiser l'historique global des messages
if "global_messages" not in st.session_state:
    st.session_state.global_messages = []

# Initialiser l'historique des analyses de documents
if "document_history" not in st.session_state:
    st.session_state.document_history = []

# Afficher l'historique global des messages
for message in st.session_state.global_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de téléchargement de fichier
new_file = st.file_uploader("Upload a new evaluation report (PDF or DOCX)", type=["pdf", "docx"], key="new_file_uploader")

# Bouton pour démarrer une nouvelle analyse
if st.button("Start New Analysis"):
    if new_file is not None:
        # Traiter le nouveau fichier
        with st.spinner("Analyzing the document..."):
            file_type = new_file.type
            if file_type == "application/pdf":
                text = extract_text_from_pdf(new_file)
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(new_file)
            else:
                st.error("Unsupported file type. Please upload a PDF or DOCX file.")
                text = ""

            if text:
                analysis = analyze_document(text)
                df = text_to_table(analysis)

                # Ajouter l'analyse à l'historique des documents
                st.session_state.document_history.append({
                    "filename": new_file.name,
                    "analysis": analysis,
                    "dataframe": df,
                    "messages": []  # Initialiser l'historique des messages pour ce document
                })

                # Mettre à jour l'état pour la nouvelle analyse
                st.session_state.current_document = new_file.name
                st.session_state.text = text
                st.session_state.analysis = analysis
                st.session_state.df = df

                # Afficher le DataFrame
                st.subheader(f"Comprehensive Analytical Synthesis of {new_file.name}:")
                st.table(df)

                # Réinitialiser la zone de saisie de texte pour une nouvelle conversation (sans utiliser st.session_state)
                # La zone de saisie se réinitialisera naturellement car elle n'a pas de `key`

    else:
        st.error("Please upload a new evaluation report to start a new analysis.")

# Zone d'entrée pour l'utilisateur (sans la clé 'key')
new_query = st.chat_input("Posez une question ici...")

# Si l'utilisateur pose une nouvelle question
if new_query:
    # Trouver l'historique du document actuel
    current_document_history = next((item for item in st.session_state.document_history if item["filename"] == st.session_state.current_document), None)

    # Ajouter la requête utilisateur à l'historique global
    st.session_state.global_messages.append({"role": "user", "content": new_query})
    with st.chat_message("user"):
        st.markdown(new_query)

    # Générer une réponse à partir du modèle
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Utiliser le texte du document actuel comme contexte
            prompt = f"Document: {st.session_state.text}\n\nQuery: {new_query}"
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            # Afficher la réponse du modèle
            st.markdown(response.text)

            # Ajouter la réponse du modèle à l'historique global
            st.session_state.global_messages.append({"role": "assistant", "content": response.text})

            # Mettre à jour l'historique des messages pour le document actuel
            if current_document_history:
                current_document_history["messages"].append({"role": "user", "content": new_query})
                current_document_history["messages"].append({"role": "assistant", "content": response.text})

# Afficher l'historique des analyses de documents dans la barre latérale
st.sidebar.title("Document Analysis History")
for item in st.session_state.document_history:
    with st.sidebar.expander(f"Analysis of {item['filename']}"):
        st.table(item["dataframe"])
        for message in item["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Bouton pour effacer l'historique global
if st.sidebar.button("Clear Global History"):
    st.session_state.global_messages = []
    st.session_state.document_history = []
    st.session_state.current_document = None
    st.session_state.text = None
    st.session_state.analysis = None
    st.session_state.df = None

