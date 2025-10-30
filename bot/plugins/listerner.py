from pyrogram.filters import new_chat_members, left_chat_member
from pyrogram.handlers import MessageHandler, ChatMemberUpdatedHandler
from pyrogram.enums import ChatMemberStatus, ChatType
from bot import bot, LOG_CHANNEL as LOG_CHANNEL_ID
from bot.helper.telegram_helper.message_utils import send_log_message
from bot.database.db_handler import DbManager

db = DbManager()

async def bot_status_handler(client, update):
    log_message = None
    me = await client.get_me()

    # Check if the bot's status has changed
    if update.old_chat_member and update.new_chat_member and update.old_chat_member.user.id == me.id and update.new_chat_member.user.id == me.id:
        # Check for demotion from administrator to member
        if update.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR and update.new_chat_member.status == ChatMemberStatus.MEMBER:
            # bot Demoted as member
            chat = update.chat
            user = update.from_user  # The user who performed the action
            if chat.type == ChatType.SUPERGROUP:
                type = 'SUPERGROUP'
            elif chat.type == ChatType.GROUP:
                type = "GROUP"
            elif chat.type == ChatType.CHANNEL:
                type = "CHANNEL"
            result = await db.update_chat_status(chat.id, 'member', None)
            if result == 'Not Found':
                result = await db.add_chat_id(chat.id, chat.title, type, 'member', None)
            if result:
                log_message = (
                    f"<b>Bot Demoted to Member</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Demoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Demoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    "<b>#ERROR</b>\n\n"
                    f"Error while updating status of chat_id {chat.id} in mongodb\n"
                    f"<b>Bot Demoted to Member</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Demoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Demoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )

        elif update.old_chat_member.status == ChatMemberStatus.MEMBER and update.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            # bot promoted as admin
            chat = update.chat
            user = update.from_user  # The user who performed the action
            promoted_user_id = update.new_chat_member.promoted_by.id if update.new_chat_member and update.new_chat_member.promoted_by else None
            if chat.type == ChatType.SUPERGROUP:
                type = 'SUPERGROUP'
            elif chat.type == ChatType.GROUP:
                type = "GROUP"
            elif chat.type == ChatType.CHANNEL:
                type = "CHANNEL"
            result = await db.update_chat_status(chat.id, 'admin', promoted_user_id)
            if result == 'Not Found':
                result = await db.add_chat_id(chat.id,chat.title, type, 'admin', promoted_user_id)
            if result:
                log_message = (
                    f"<b>Bot Promoted to Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Promoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Promoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    "<b>#ERROR</b>\n\n"
                    f"Error While Updating Status Chat_id {chat.id} in mongodb\n"
                    f"<b>Bot Promoted to Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Promoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Promoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )
        elif update.old_chat_member.status == ChatMemberStatus.BANNED and update.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            chat = update.chat
            user = update.from_user
            promoted_user_id = update.new_chat_member.promoted_by.id if update.new_chat_member and update.new_chat_member.promoted_by else None
            if chat.type == ChatType.SUPERGROUP:
                type = 'SUPERGROUP'
            elif chat.type == ChatType.GROUP:
                type = "GROUP"
            elif chat.type == ChatType.CHANNEL:
                type = "CHANNEL"
            # readd in old group as admin
            result = await db.add_chat_id(chat.id, chat.title, type, 'admin', promoted_user_id)
            if result:
                log_message = (
                    f"<b>Bot Readded to chat as Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Promoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Promoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    "<b>#ERROR</b>\n\n"
                    f"Error while adding chat_id {chat.id} in mongodb\n"
                    f"<b>Bot Readded to chat as Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Promoted by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Promoted by Username:</b> @{user.username if user.username else 'N/A'}\n"
                )

    elif update.new_chat_member and update.new_chat_member.user.id == me.id:
        if not update.old_chat_member and update.new_chat_member.status == ChatMemberStatus.MEMBER:
            chat = update.chat
            user = update.from_user
            if chat.type == ChatType.SUPERGROUP:
                type = 'SUPERGROUP'
            elif chat.type == ChatType.GROUP:
                type = "GROUP"
            elif chat.type == ChatType.CHANNEL:
                type = "CHANNEL"
            # add in group as member
            result = await db.add_chat_id(chat.id, chat.title, type, 'member', None)
            if result:
                log_message = (
                    f"<b>Bot Added in Chat as Member</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Added by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Added by Username</b>: @{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    '<b>#ERROR</b>\n\n'
                    f"Error while adding chat_id {chat.id} in mongodb"
                    f"<b>Bot Added in Chat as Member</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Added by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Added by Username</b>: @{user.username if user.username else 'N/A'}\n"
                )
        elif not update.old_chat_member and update.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            chat = update.chat
            user = update.from_user
            promoted_user_id = update.new_chat_member.promoted_by.id if update.new_chat_member and update.new_chat_member.promoted_by else None
            if chat.type == ChatType.SUPERGROUP:
                type = 'SUPERGROUP'
            elif chat.type == ChatType.GROUP:
                type = "GROUP"
            elif chat.type == ChatType.CHANNEL:
                type = "CHANNEL"
            # Add in group as admin
            result = await db.add_chat_id(chat.id, chat.title, type, 'admin', promoted_user_id)
            if result:
                log_message = (
                    f"<b>Bot Added in Chat as Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Added by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Added by Username</b>: @{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    "<b>#ERROR</b>\n\n"
                    f"Error while adding chat_id {chat.id} in mongodb\n"
                    f"<b>Bot Added in Chat as Admin</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Added by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Added by Username</b>: @{user.username if user.username else 'N/A'}\n"
                )

    elif update.old_chat_member and update.old_chat_member.user.id == me.id:
        # Remove from group
        if update.old_chat_member.status == ChatMemberStatus.MEMBER:
                # Check if new_chat_member is None, which indicates the bot was removed
                if update.new_chat_member is None or update.new_chat_member.status == ChatMemberStatus.LEFT:
                    chat = update.chat
                    user = update.from_user  # The user who performed the action
                    result = await db.del_chat_id(chat.id)
                    # Prepare the log message for removal
                    if result:
                        log_message = (
                            f"<b>Bot Removed from Chat</b>\n\n"
                            f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                            f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                            f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                            f"<b>Removed by User ID:</b> <code>{user.id}</code>\n"
                            f"<b>Removed by Username:</b> <code>@{user.username if user.username else 'N/A'}\n"
                        )
                    else:
                        log_message = (
                            "<b>#ERROR</b>\n\n"
                            f"Error while deleteing chat_id {chat.id} in mongodb"
                            f"<b>Bot Removed from Chat</b>\n\n"
                            f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                            f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                            f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                            f"<b>Removed by User ID:</b> <code>{user.id}</code>\n"
                            f"<b>Removed by Username:</b> <code>@{user.username if user.username else 'N/A'}\n"
                        )
        elif update.new_chat_member is None and update.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            chat = update.chat
            user = update.from_user
            result = await db.del_chat_id(chat.id)
            # Remove from channel
            if result:
                log_message = (
                    f"<b>Bot Removed from Channel</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Removed by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Removed by Username:</b> <code>@{user.username if user.username else 'N/A'}\n"
                )
            else:
                log_message = (
                    "<b>#ERROR</b>\n\n"
                    f"Error while delteing chat_id {chat.id} in mongodb\n"
                    f"<b>Bot Removed from Channel</b>\n\n"
                    f"<b>Chat Title:</b> <code>{chat.title}</code>\n"
                    f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
                    f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
                    f"<b>Removed by User ID:</b> <code>{user.id}</code>\n"
                    f"<b>Removed by Username:</b> <code>@{user.username if user.username else 'N/A'}\n"
                )
    if log_message is not None:
        await send_log_message(text=log_message)
    else:
        return

bot.add_handler(
    ChatMemberUpdatedHandler(
        bot_status_handler
    )
)
