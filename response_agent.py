import logging
from functools import lru_cache
import time
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

# Cache the results of generate_text using lru_cache
@lru_cache(maxsize=128)  # You can adjust maxsize based on your memory constraints
def generate_text_cached(query, combined_input):
    """
    Generates text using the Gemini model, with caching.
    Uses both the query and combined_input to construct the prompt.
    """
    prompt = f"""
    Query: {query}
    Combined Input: {combined_input}

    Answer the query based on the provided combined input.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error generating response for query: {query} - {str(e)}")
        return None  # Return None to indicate an error


def generate_response(query, combined_input):
    """
    Generates text using the Gemini model with caching.
    Measures and logs the time taken for text generation.
    Handles potential errors during text generation.
    """
    start_time = time.time()
    generated_text = generate_text_cached(query, combined_input)
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Time taken to generate text: {elapsed_time:.4f} seconds")

    if generated_text:
        return generated_text
    else:
        return "Sorry, I couldn't generate a response at the moment."


