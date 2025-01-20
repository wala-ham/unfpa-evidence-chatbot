# storage_utils.py
import os
import re
from google.cloud import storage
import streamlit as st

# --- Storage Utilities ---
def upload_to_storage(bucket_name, source_file_name, destination_blob_name):
    """
    Uploads a file to Google Cloud Storage.

    :param bucket_name: Name of the bucket in GCP.
    :param source_file_name: Path to the file to upload.
    :param destination_blob_name: Destination path in the bucket.
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        print(f"File {source_file_name} uploaded to {destination_blob_name} in bucket {bucket_name}.")
        return True
    except Exception as e:
        print(f"Error uploading file to GCS: {e}")
        return False

def download_from_storage(bucket_name, source_blob_name, destination_file_name):
    """
    Downloads a file from Google Cloud Storage.

    :param bucket_name: Name of the bucket in GCP.
    :param source_blob_name: Path to the file in the bucket.
    :param destination_file_name: Local path to save the downloaded file.
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"File {source_blob_name} downloaded to {destination_file_name}.")
        return True
    except Exception as e:
        print(f"Error downloading file from GCS: {e}")
        return False

def sanitize_filename(filename, max_length=100):
    """
    Sanitizes a filename by removing invalid characters and truncating to a maximum length.

    :param filename: Original filename.
    :param max_length: Maximum length for the filename.
    """
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
    filename = filename.lower()
    return filename[:max_length]

# --- Firebase Authentication Utilities ---
def save_messages_to_cloud(user_name, messages):
    """Save the user's messages to cloud storage."""
    bucket_name = st.secrets["GCP_BUCKET_NAME"]
    filename = f"{user_name}_messages.json"
    sanitized_filename = sanitize_filename(filename)
    upload_to_storage(bucket_name, sanitized_filename, messages)

def load_messages_from_cloud(user_name):
    """Load the user's messages from cloud storage."""
    bucket_name = st.secrets["GCP_BUCKET_NAME"]
    filename = f"{user_name}_messages.json"
    sanitized_filename = sanitize_filename(filename)
    return download_from_storage(bucket_name, sanitized_filename, f"tmp_{sanitized_filename}")

