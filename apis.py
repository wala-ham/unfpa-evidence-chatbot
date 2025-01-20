from flask import Flask, request, jsonify, send_file
import os
import base64
import subprocess
import time
import re
from flask import Flask, request, jsonify
import PyPDF2
from docx import Document
import pandas as pd
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold
from google.cloud import storage  # Install with: pip install google-cloud-storage

# Importer les fonctions pré-définies
from retrieval_agent import retrieve_chunks
from response_agent import generate_response
from visualization_agent import needs_graphic, generate_graphic
from storage_utils import upload_to_storage, sanitize_filename
from speech_to_text import record_audio  # Importer la fonction depuis speech_to_text



# Initialiser l'application Flask
app = Flask(__name__)

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
        print(f"Erreur lors de la conversion du texte en tableau : {e}")
        return pd.DataFrame()


# Répertoire pour sauvegarder les images générées
STATIC_IMG_DIR = "static_img"
os.makedirs(STATIC_IMG_DIR, exist_ok=True)

# Configure Google Cloud Storage (replace with your bucket name)
BUCKET_NAME = 'unfpa-444213.appspot.com'  # Replace with your bucket name

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Récupérer la requête utilisateur
        data = request.json
        query = data.get("query")
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        # Étape 1 : Récupérer des documents pertinents
        chunks = retrieve_chunks(query)
        combined_input = " ".join([chunk["chunk"] for chunk in chunks]) if chunks else query

        # Étape 2 : Générer une réponse à partir du modèle
        response = generate_response(query, combined_input)

        # Étape 3 : Vérifier si un graphique est nécessaire
        image_base64 = None
        image_filename = None
        graphic_url = None  # Initialize graphic_url
        if needs_graphic(query, response):
            code_snippet = generate_graphic(query, response)
            if code_snippet:
                try:
                    # Sanitize the query to create a valid filename
                    sanitized_query = sanitize_filename(query)

                    # Include a timestamp to ensure unique filenames
                    timestamp = int(time.time())
                    image_filename = f"{sanitized_query}_{timestamp}_generated_graph.png"
                    graphic_path = os.path.join(STATIC_IMG_DIR, image_filename)

                    # Ajouter l'instruction pour sauvegarder l'image au bon endroit
                    code_snippet += f"\nplt.savefig('{graphic_path}')"

                    # Exécuter dynamiquement le code généré
                    exec_globals = {"__name__": "__main__"}
                    exec_locals = {}
                    exec(code_snippet, exec_globals, exec_locals)

                    # Upload to GCS
                    gcs_destination = f"images/{image_filename}"
                    if upload_to_storage(BUCKET_NAME, graphic_path, gcs_destination):
                        print(f"Graphic successfully uploaded to GCS at: {gcs_destination}")
                        graphic_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{gcs_destination}"
                    else:
                        print("Failed to upload the graphic to GCS.")

                except Exception as e:
                    print(f"Failed to generate the graphic: {e}")
                    return jsonify({"error": f"Failed to generate graphic: {str(e)}"}), 500

        # Préparer la réponse finale
        response_data = {
            "query": query,
            "response": response,
            "graphic_url": graphic_url  # Return the GCS URL
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/static_img/<filename>", methods=["GET"])
def get_image(filename):
    """Endpoint pour récupérer les images générées."""
    file_path = os.path.join(STATIC_IMG_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="image/png")
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/transcribe', methods=['POST'])
def transcribe_api():
    try:
        # Record audio
        transcript = record_audio()

        if transcript:
            return jsonify({'transcript': transcript}), 200
        else:
            return jsonify({'error': 'No audio transcribed'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_api():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        file_type = file.content_type
        if file_type == 'application/pdf':
            text = extract_text_from_pdf(file)
        elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_text_from_docx(file)
        else:
            return jsonify({'error': 'Unsupported file type. Please upload a PDF or DOCX file.'}), 400

        if text:
            analysis = analyze_document(text)
            df = text_to_table(analysis)
            # Convert DataFrame to JSON for API response
            table_json = df.to_json(orient='records')
            return jsonify({'analysis': analysis, 'table': table_json}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/query', methods=['POST'])
def query_api():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        try:
            file_type = file.content_type
            if file_type == 'application/pdf':
                text = extract_text_from_pdf(file)
            elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                text = extract_text_from_docx(file)
            else:
                return jsonify({'error': 'Unsupported file type. Please upload a PDF or DOCX file.'}), 400

            if text:
                # Get the query from the request parameters
                query = request.form.get('query') 

                if not query:  # Check if query is provided
                    return jsonify({'error': 'Missing query'}), 400

                prompt = f"Document: {text}\n\nQuery: {query}"
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )

                return jsonify({'response': response.text}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)