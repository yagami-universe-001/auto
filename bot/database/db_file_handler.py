import base64
import re
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient
from umongo import Document, fields, Instance, ValidationError
from pyrogram.file_id import FileId  
from struct import pack
import logging
from datetime import datetime
import pytz

from bot import FILES_DATABASE_URL

#duguggd8wgygw
logger = logging.getLogger(__name__)

# Database Configuration
client = AsyncIOMotorClient(FILES_DATABASE_URL)
fdb = client.HUB4VF
instance = Instance.from_db(fdb)


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


@instance.register
class Media(Document):
    """
    Media document schema for storing file metadata in the database.
    """
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_languages = fields.ListField(fields.StrField(), allow_none=True)
    file_quality = fields.StrField(allow_none=True)
    file_season = fields.StrField(allow_none=True)
    file_episode = fields.StrField(allow_none=True)
    file_year = fields.StrField(allow_none=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    created_at = fields.DictField()  # Remove default to set it manually

    class Meta:
        collection_name = 'hubfiles'


async def save_file(media) -> tuple[bool, int]:
    """
    Saves media information to the database.
    """
    try:
        if media.document:
            iron_media = media.document
            file_type = "document"
            file_name = iron_media.file_name
            file_size = iron_media.file_size
            mime_type = iron_media.mime_type
        elif media.video:
            iron_media = media.video
            file_type = "video"
            file_name = iron_media.file_name
            file_size = iron_media.file_size
            mime_type = iron_media.mime_type
        elif media.audio:
            iron_media = media.audio
            file_type = "audio"
            file_name = iron_media.file_name
            file_size = iron_media.file_size
            mime_type = iron_media.mime_type
        if not iron_media:
            logger.error("Media does not have a valid file_id.")
            return False, 2
        
        file_id, file_ref = unpack_new_file_id(iron_media.file_id)
        iron_name = re.sub(r"@\w+|(_|\-|\.|\+|\#|\$|%|\^|&|\*|\(|\)|!|~|`|,|;|:|\"|\'|\?|/|<|>|\[|\]|\{|\}|=|\||\\)", " ", str(file_name))
        iron_name = re.sub(r"\s+", " ", iron_name)
        # Get current time in Kolkata time zone
        kolkata_tz = pytz.timezone("Asia/Kolkata")
        created_at = datetime.now(kolkata_tz)  # Get current time in Kolkata

        # Format created_at to the desired structure
        formatted_created_at = {
            "date": created_at.strftime("%Y-%m-%d"),  # Format date
            "time": created_at.strftime("%H:%M:%S")   # Format time
        }

        # Initialize default values
        file_languages = None
        file_quality = None
        file_season = None
        file_episode = None
        file_year = None

        # Use caption if available, otherwise fall back to file_name
        caption_text = media.caption.html if media.caption else None
        text_to_search = caption_text if caption_text else file_name

        # Extract values from the caption or file_name
        if text_to_search:
            search_text = text_to_search.lower()
            file_season = extract_season(search_text)
            file_year = extract_year(search_text)
            file_episode = extract_episode(search_text)
            file_languages = extract_languages(search_text)
            file_quality = extract_quality(search_text)
        # Create a Media object
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=iron_name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            caption=caption_text,
            file_languages=file_languages,
            file_quality=file_quality,
            file_season=file_season,
            file_episode=file_episode,
            file_year=file_year,
            created_at=formatted_created_at  # Set formatted timestamp
        )


        await file.commit()
        logger.info(f"File '{iron_name}' saved successfully in the database.")
        return True, 1

    except ValidationError as e:
        logger.error(f"Validation error while saving file: {e}")
        return False, 2

    except DuplicateKeyError:
        logger.warning(f"File '{iron_media.file_name}' is already saved in the database.")
        return False, 0
    
def extract_year(text):
    # Remove specified special characters
    text = re.sub(r'[_\.=+\-(){}\[\]\\|,;#@/:]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert all text to lowercase
    text = text.lower()
    
    # Regular expression pattern to find year information
    pattern = r"\b(19|20)\d{2}\b"  # Matches years from 1900 to 2099

    # Search for the pattern in the text
    match = re.search(pattern, text)

    # Extract and return the year if found
    if match:
        year = match.group(0)
        return f"{year}"
    else:
        return None

def extract_season(text):
    # Remove specified special characters
    text = re.sub(r'[_\.=+\-(){}\[\]\\|,;#@/:]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert all text to lowercase
    text = text.lower()
    
    # Regular expression pattern to find season information
    pattern = r"season\s*(\d+)|s\s*(\d+)|season\s*(\d{1,3})|s(\d{1,3})|s(\d{1,3})|s(\d{1,3})|season(\d{1,3})"

    # Search for the pattern in the text
    match = re.search(pattern, text)

    # Extract and return the season number if found
    if match:
        # Check which group matched and get the season number
        season_number = match.group(1) or match.group(2) or match.group(3) or match.group(4) or match.group(5) or match.group(6) or match.group(7)
        return f"{season_number.zfill(2)}"  # Zero-pad to 2 digits
    else:
        return None

def extract_episode(text):
    # Remove specified special characters
    text = re.sub(r'[_\.=+\-(){}\[\]\\|,;#@/:]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert all text to lowercase
    text = text.lower()
    
    # Regular expression pattern to find episode information
    pattern = r"episode\s*(\d+)|ep\s*(\d+)|e\s*(\d+)|ep(\d+)|e(\d+)|episode\s*(\d{1,3})|e(\d{1,3})|episode(\d{1,3})"

    # Search for the pattern in the text
    match = re.search(pattern, text)

    # Extract and return the episode number if found
    if match:
        # Check which group matched and get the episode number
        episode_number = match.group(1) or match.group(2) or match.group(3) or match.group(4) or match.group(5) or match.group(6) or match.group(7) or match.group(8)
        return f"{episode_number.zfill(2)}"  # Zero-pad to 2 digits
    else:
        return None

def extract_languages(text):
    # Flat list of languages and their short forms
    languages = [
        'hindi', 'hin',
        'english', 'eng',
        'gujarati', 'guj',
        'marathi', 'mar',
        'tamil', 'tam',
        'telugu', 'tel',
        'malayalam', 'mal',
        'bengali', 'ben',
        'punjabi', 'pun',
        'kannada', 'kan',
        'odia', 'odi',
        'assamese', 'ass',
        'urdu', 'urd',
        'sindhi', 'sin',
        'kashmiri', 'kas',
        'korean', 'kor',
    ]
    
    # Create a mapping of abbreviations to full names
    lang_map = {languages[i + 1]: languages[i] for i in range(0, len(languages), 2)}
    
    # Remove specified special characters
    text = re.sub(r'[_\.=+\-(){}\[\]\\|,;#@/:]', ' ', text)  # Replace specified special characters with a space
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace

    # Normalize text to lowercase for matching
    text_lower = text.lower()
    
    # Find and collect languages present in the text (full language names) using word boundaries
    found_languages = [languages[i] for i in range(0, len(languages), 2) if re.search(r'\b' + re.escape(languages[i]) + r'\b', text_lower)]
    
    # Find and collect abbreviations present in the text using word boundaries
    found_abbreviations = [languages[i + 1] for i in range(0, len(languages), 2) if re.search(r'\b' + re.escape(languages[i + 1]) + r'\b', text_lower)]
    
    # Check for abbreviations and return long names
    long_names = [lang_map[abbrev] for abbrev in found_abbreviations if abbrev in lang_map]
    
    # Combine found languages with their long names into a flat list and remove duplicates using set()
    return list(set(found_languages + long_names))  # Use set to avoid duplicate

def extract_quality(text):
    # Common video quality indicators
    qualities = [
        '144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p'
    ]
    
    # Remove specified special characters
    text = re.sub(r'[_\.=+\-(){}\[\]\\|,;#@/:]', ' ', text)  # Replace specified special characters with a space
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace

    # Normalize text to lowercase for matching
    text_lower = text.lower()
    
    # Find and collect qualities present in the text
    found_qualities = [quality for quality in qualities if quality in text_lower]
    
    # Return a comma-separated string of found qualities or an empty string if none found
    return ', '.join(set(found_qualities)) if found_qualities else None
