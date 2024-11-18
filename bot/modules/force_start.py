from nekozee.filters import command
from nekozee.handlers import MessageHandler

from bot import (
    OWNER_ID,
    bot,
    queued_up,
    queued_dl,
    queue_dict_lock,
    task_dict,
    task_dict_lock,
    user_data,
)
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_task_by_gid
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    send_message
)
from ..helper.ext_utils.task_manager import (
    start_dl_from_queued,
    start_up_from_queued
)


@new_task
async def remove_from_queue(_, message):
    user_id = (
        message.from_user.id
        if message.from_user
        else message.sender_chat.id
    )
    msg = message.text.split()
    status = (
        msg[1]
        if len(msg) > 1
        and msg[1] in [
            "fd",
            "fu"
        ]
        else ""
    )
    if (
        status and len(msg) > 2
        or not status and len(msg) > 1
    ):
        gid = msg[2] if status else msg[1]
        task = await get_task_by_gid(gid)
        if task is None:
            smsg = await send_message(
                message,
                f"GID: <code>{gid}</code> Not Found."
            )
            await auto_delete_message(
                message,
                smsg
            )
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if task is None:
            smsg = await send_message(
                message,
                "This is not an active task!"
            )
            await auto_delete_message(
                message,
                smsg
            )
            return
    elif len(msg) in {
        1,
        2
    }:
        msg = (
            "Reply to an active Command message which was used to start the download"
            f" or send <code>/{BotCommands.ForceStartCommand[0]} GID</code> to force start download and upload! Add you can use /cmd <b>fd</b> to force downlaod only or /cmd <b>fu</b> to force upload only!"
        )
        smsg = await send_message(
            message,
            msg
        )
        await auto_delete_message(
            message,
            smsg
        )
        return
    if (
        OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (
            user_id not in user_data
            or not user_data[user_id].get("is_sudo")
        )
    ):
        smsg = await send_message(
            message,
            "This task is not for you!"
        )
        await auto_delete_message(
            message,
            smsg
        )
        return
    listener = task.listener
    msg = ""
    async with queue_dict_lock:
        if status == "fu":
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Task have been force started to upload!"
        elif status == "fd":
            listener.force_download = True
            if listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Task have been force started to download only!"
        else:
            listener.force_download = True
            listener.force_upload = True
            if listener.mid in queued_up:
                await start_up_from_queued(listener.mid)
                msg = "Task have been force started to upload!"
            elif listener.mid in queued_dl:
                await start_dl_from_queued(listener.mid)
                msg = "Task have been force started to download and upload will start once download finish!"
    if msg:
        smsg = await send_message(
            message,
            msg
        )
        await auto_delete_message(
            message,
            smsg
        )


bot.add_handler( # type: ignore
    MessageHandler(
        remove_from_queue,
        filters=command(
            BotCommands.ForceStartCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
