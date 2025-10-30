import os
import random
import string
from bot import bot, LOGGER

generated_ids = set()

def generate_unique_id(length=10):
    characters = string.ascii_letters + string.digits  # Include uppercase, lowercase letters, and digits
    while True:
        unique_id = ''.join(random.choices(characters, k=length))  # Generate a random ID
        if unique_id not in generated_ids:  # Check for uniqueness
            generated_ids.add(unique_id)  # Add to the set of generated IDs
            return unique_id
        
async def download_file(message):
    try:
        # Define the download directory
        download_dir = "downloads/media"
        
        # Create the directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)

        # Initialize file_name and file_extension
        file_name = None
        file_extension = None

        # Check if the message has a document or video
        if message.document:
            file_name = message.document.file_name
            file_extension = os.path.splitext(file_name)[1]  # Get the file extension
        elif message.video:
            file_name = message.video.file_name
            file_extension = os.path.splitext(file_name)[1]  # Get the file extension
        if len(file_extension) == 0:
            file_extension = ".mp4"
        # Generate a unique ID
        unique_id = generate_unique_id()

        # Construct the full file path with the unique ID and the original file extension
        file_path = os.path.join(download_dir, f"{unique_id}{file_extension}")

        # Download the file
        await bot.download_media(message, file_path)
        
        # Return the file path
        return file_path, file_name
    except Exception as e:
        LOGGER.error(f"Error During download file: {e}")