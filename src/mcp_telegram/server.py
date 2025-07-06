from __future__ import annotations

import logging
import os
from typing import Any
from fastmcp import FastMCP
from mcp.types import TextContent, ImageContent, EmbeddedResource
from telethon import TelegramClient, custom, functions, types

from mcp_telegram.telegram import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

port = int(os.getenv("PORT", 8000))
mcp = FastMCP("mcp-telegram", port=port)


@mcp.tool
async def list_dialogs(
    unread: bool = False,
    archived: bool = False,
    ignore_pinned: bool = False,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """List available dialogs, chats and channels."""
    logger.info("method[ListDialogs] unread=%s archived=%s ignore_pinned=%s", unread, archived, ignore_pinned)

    response: list[TextContent] = []
    try:
        async with create_client() as client:
            dialog: custom.dialog.Dialog
            async for dialog in client.iter_dialogs(archived=archived, ignore_pinned=ignore_pinned, limit=10):
                if unread and dialog.unread_count == 0:
                    continue
                msg = (
                    f"name='{dialog.name}' id={dialog.id} "
                    f"unread={dialog.unread_count} mentions={dialog.unread_mentions_count}"
                )
                response.append(TextContent(type="text", text=msg))
    except Exception as e:
        logger.error("Error listing dialogs: %s", e)
        response.append(TextContent(type="text", text=f"Error: {str(e)}"))

    return response


@mcp.tool
async def list_messages(
    chat_id: int,
    unread: bool = False,
    limit: int = 100,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """
    List messages in a given dialog, chat or channel. The messages are listed in order from newest to oldest.

    If `unread` is set to `True`, only unread messages will be listed. Once a message is read, it will not be
    listed again.

    If `limit` is set, only the last `limit` messages will be listed. If `unread` is set, the limit will be
    the minimum between the unread messages and the limit.
    """
    logger.info("method[ListMessages] chat_id=%s unread=%s limit=%s", chat_id, unread, limit)

    response: list[TextContent] = []
    try:
        async with create_client() as client:
            result = await client(functions.messages.GetPeerDialogsRequest(peers=[chat_id]))
            if not result:
                raise ValueError(f"Channel not found: {chat_id}")

            if not isinstance(result, types.messages.PeerDialogs):
                raise TypeError(f"Unexpected result: {type(result)}")

            for dialog in result.dialogs:
                logger.debug("dialog: %s", dialog)
            for message in result.messages:
                logger.debug("message: %s", message)

            iter_messages_args: dict[str, Any] = {
                "entity": chat_id,
                "reverse": False,
            }
            if unread:
                iter_messages_args["limit"] = min(dialog.unread_count, limit)
            else:
                iter_messages_args["limit"] = limit

            logger.debug("iter_messages_args: %s", iter_messages_args)
            async for message in client.iter_messages(**iter_messages_args):
                logger.debug("message: %s", type(message))
                if isinstance(message, custom.Message) and message.text:
                    logger.debug("message: %s", message.text)
                    response.append(TextContent(type="text", text=message.text))
    except Exception as e:
        logger.error("Error listing messages: %s", e)
        response.append(TextContent(type="text", text=f"Error: {str(e)}"))

    return response


# reply to message
@mcp.tool
async def reply_to_message(
    chat_id: int,
    message_id: int,
    text: str,
) -> None:
    """Reply to a message."""
    logger.info("method[ReplyToMessage] message_id=%s text=%s", message_id, text)
    try:
        async with create_client() as client:
            await client.reply_to_message(chat_id, message_id, text)
    except Exception as e:
        logger.error("Error replying to message: %s", e)
        raise e


if __name__ == "__main__":
    # Use stdio transport as it's most compatible
    logger.info("Starting MCP Telegram server with stdio transport")
    mcp.run(transport="streamable-http")
