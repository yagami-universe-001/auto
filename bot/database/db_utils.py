import re

from bot import config_dict

from bot.database.db_handler import DbManager
from bot.database.db_file_handler import Media

USE_CAPTION_FILTER = config_dict['USE_CAPTION_FILTER']

async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails

async def get_search_results(
        chat_id=None, 
        query=None, 
        file_type=None, 
        file_quality=None, 
        file_language=None, 
        file_season=None,
        file_episode=None,
        file_year=None,
        file_date=None,
        max_results=10, 
        offset=0, 
        filter=False
    ):
    """For given query return (results, next_offset)"""
    query = query.strip()
    
    # Prepare the regex pattern for the query
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []

    # Build the filter dictionary
    filter = {'$or': [{'file_name': regex}, {'caption': regex}]} if USE_CAPTION_FILTER else {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    if file_quality:
        filter['file_quality'] = file_quality

    if file_language:
        # Ensure language is in lowercase for case-insensitive matching
        filter['file_languages'] = {'$elemMatch': {'$regex': re.compile(file_language, flags=re.IGNORECASE)}}
    
    if file_season:
        filter['file_season'] = file_season

    if file_episode:
        filter['file_episode'] = file_episode

    if file_year:
        filter['file_year'] = file_year

    if file_date:
        filter['created_at.date'] = file_date

    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ''

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort('$natural', -1)
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)
    return files, next_offset, total_results


def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])
    

