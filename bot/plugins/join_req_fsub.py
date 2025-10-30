from pyrogram import filters, enums
from pyrogram.types import ChatJoinRequest
from pyrogram.handlers import ChatJoinRequestHandler
from bot.database.db_handler import DbManager
from bot import config_dict, bot, LOGGER
from bot.helper.telegram_helper.message_utils import process_channel

db = DbManager()

AUTH_CHANNEL = config_dict['FSUB_IDS'].split()

# Initialize variables
AUTH_CHANNEL_1 = None
AUTH_CHANNEL_2 = None
AUTH_CHANNEL_3 = None

chat_join_request_handlers = []

def initialize_auth_channels():
    global AUTH_CHANNEL_1, AUTH_CHANNEL_2, AUTH_CHANNEL_3
    AUTH_CHANNEL = config_dict['FSUB_IDS'].split()
    
    if len(AUTH_CHANNEL) == 1:
        AUTH_CHANNEL_1 = int(AUTH_CHANNEL[0])
        AUTH_CHANNEL_2 = None
        AUTH_CHANNEL_3 = None
    elif len(AUTH_CHANNEL) == 2:
        AUTH_CHANNEL_1 = int(AUTH_CHANNEL[0])
        AUTH_CHANNEL_2 = int(AUTH_CHANNEL[1])
        AUTH_CHANNEL_3 = None
    elif len(AUTH_CHANNEL) >= 3:
        AUTH_CHANNEL_1 = int(AUTH_CHANNEL[0])
        AUTH_CHANNEL_2 = int(AUTH_CHANNEL[1])
        AUTH_CHANNEL_3 = int(AUTH_CHANNEL[2])
    return
# Assuming you have a global list to track handlers
chat_join_request_handlers = []

def add_handlers():
    try:
        if len(chat_join_request_handlers) != 0:
            # Remove only ChatJoinRequestHandler handlers
            for handler in chat_join_request_handlers:
                bot.remove_handler(handler)
                LOGGER.critical(f"Remove Handler: {handler}")

        # Clear the list of handlers
        chat_join_request_handlers.clear()

        # Add new handlers
        if AUTH_CHANNEL_1:
            handler_a = ChatJoinRequestHandler(join_reqs_a, filters=filters.chat(AUTH_CHANNEL_1))
            bot.add_handler(handler_a)
            chat_join_request_handlers.append(handler_a)
            LOGGER.info(f"Added handler for AUTH_CHANNEL_1: {AUTH_CHANNEL_1}")

        if AUTH_CHANNEL_2:
            handler_b = ChatJoinRequestHandler(join_reqs_b, filters=filters.chat(AUTH_CHANNEL_2))
            bot.add_handler(handler_b)
            chat_join_request_handlers.append(handler_b)
            LOGGER.info(f"Added handler for AUTH_CHANNEL_2: {AUTH_CHANNEL_2}")

        if AUTH_CHANNEL_3:
            handler_c = ChatJoinRequestHandler(join_reqs_c, filters=filters.chat(AUTH_CHANNEL_3))
            bot.add_handler(handler_c)
            chat_join_request_handlers.append(handler_c)
            LOGGER.info(f"Added handler for AUTH_CHANNEL_3: {AUTH_CHANNEL_3}")

        LOGGER.info("All handlers added successfully.")
    except Exception as e:
        LOGGER.error(f"Error while adding fsub handler: {e}")

async def join_reqs_a(client, message: ChatJoinRequest):
    if not AUTH_CHANNEL_1:
        return
    user_check, user_id = await db.check_requestjoined_fsub_user(AUTH_CHANNEL_1, message.from_user.id)
    if user_check == True:
        return
    else:
        await db.add_requestjoined_fsub_user(AUTH_CHANNEL_1, message.from_user.id)

async def join_reqs_b(client, message: ChatJoinRequest):
    if not AUTH_CHANNEL_2:
        return
    user_check, user_id = await db.check_requestjoined_fsub_user(AUTH_CHANNEL_2, message.from_user.id)
    if user_check == True:
        return
    else:
        await db.add_requestjoined_fsub_user(AUTH_CHANNEL_2, message.from_user.id)

async def join_reqs_c(client, message: ChatJoinRequest):
    if not AUTH_CHANNEL_3:
        return
    user_check, user_id = await db.check_requestjoined_fsub_user(AUTH_CHANNEL_3, message.from_user.id)
    if user_check == True:
        return
    else:
        await db.add_requestjoined_fsub_user(AUTH_CHANNEL_3, message.from_user.id)

initialize_auth_channels()
add_handlers()
