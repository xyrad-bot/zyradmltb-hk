from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
    sleep,
)
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import (
    partial,
    wraps
)
from os import cpu_count
from httpx import AsyncClient

from nekozee.types import BotCommand

from bot import (
    user_data,
    config_dict,
    bot_loop,
    extra_buttons
)
from .help_messages import (
    YT_HELP_DICT,
    MIRROR_HELP_DICT,
    CLONE_HELP_DICT,
)
from .telegraph_helper import telegraph
from ..telegram_helper.button_build import ButtonMaker
from ..telegram_helper.bot_commands import BotCommands

COMMAND_USAGE = {}

max_workers = min(
    10000,
    (
        cpu_count()
        or 0
    ) + 4
)
THREAD_POOL = ThreadPoolExecutor(max_workers=max_workers)


class SetInterval:
    def __init__(
            self,
            interval,
            action,
            *args,
            **kwargs
        ):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(
            self._set_interval(
                *args,
                **kwargs
            )
        )

    async def _set_interval(self, *args, **kwargs):
        while True:
            await sleep(self.interval)
            await self.action(
                *args,
                **kwargs
            )

    def cancel(self):
        self.task.cancel()


def _build_command_usage(help_dict, command_key):
    buttons = ButtonMaker()
    for name in list(help_dict.keys())[1:]:
        buttons.data_button(
            name,
            f"help {command_key} {name}"
        )
    buttons.data_button(
        "ᴄʟᴏꜱᴇ",
        "help close"
    )
    COMMAND_USAGE[command_key] = [
        help_dict["main"],
        buttons.build_menu(2)
    ]
    buttons.reset()


def create_help_buttons():
    _build_command_usage(
        MIRROR_HELP_DICT,
        "mirror"
    )
    _build_command_usage(
        YT_HELP_DICT,
        "yt"
    )
    _build_command_usage(
        CLONE_HELP_DICT,
        "clone"
    )

def bt_selection_buttons(id_):
    gid = (
        id_[:12]
        if len(id_) > 25
        else id_
    )
    pincode = "".join(
        [
            n
            for n
            in id_
            if n.isdigit()
        ][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict["BASE_URL"]
    if config_dict["WEB_PINCODE"]:
        buttons.url_button(
            "ꜱᴇʟᴇᴄᴛ ꜰɪʟᴇꜱ",
            f"{BASE_URL}/app/files/{id_}"
        )
        buttons.data_button(
            "ᴘɪɴᴄᴏᴅᴇ",
            f"sel pin {gid} {pincode}"
        )
    else:
        buttons.url_button(
            "ꜱᴇʟᴇᴄᴛ ꜰɪʟᴇꜱ",
            f"{BASE_URL}/app/files/{id_}?pin_code={pincode}"
        )
    buttons.data_button(
        "ᴅᴏɴᴇ ꜱᴇʟᴇᴄᴛɪɴɢ",
        f"sel done {gid} {id_}"
    )
    buttons.data_button(
        "ᴄʟᴏꜱᴇ",
        f"sel cancel {gid}"
    )
    return buttons.build_menu(2)


def extra_btns(buttons):
    if extra_buttons:
        for (
            btn_name,
            btn_url
        ) in extra_buttons.items():
            buttons.url_button(
                btn_name,
                btn_url
            )
    return buttons


async def set_commands(client):
    if config_dict["SET_COMMANDS"]:
        await client.set_bot_commands([
            BotCommand(
                f"{BotCommands.MirrorCommand[0]}",
                "Mirror direct links using Aria2c"
            ),
            BotCommand(
                f"{BotCommands.QbMirrorCommand[0]}",
                "Mirror Qbit-torrent supported links or files"
            ),
            BotCommand(
                f"{BotCommands.YtdlCommand[0]}",
                "Mirror YT-DLP supported links"
            ),
            BotCommand(
                f"{BotCommands.LeechCommand[0]}",
                "Leech direct links using Aria2c"
            ),
            BotCommand(
                f"{BotCommands.QbLeechCommand[0]}",
                "Leech Qbit-torrent supported links or files"
            ),
            BotCommand(
                f"{BotCommands.YtdlLeechCommand[0]}",
                "Leech YT-DLP supported links"
            ),
            BotCommand(
                f"{BotCommands.CloneCommand}",
                "Copy file or folder to the drive"
            ),
            BotCommand(
                f"{BotCommands.CountCommand}",
                "[Drive URL]: Count file or folder in Google Drive"
            ),
            BotCommand(
                f"{BotCommands.StatusCommand[0]}",
                "Get all tasks status message"
            ),
            BotCommand(
                f"{BotCommands.StatsCommand[0]}",
                "Check bot stats"
            ),
            BotCommand(
                f"{BotCommands.CancelTaskCommand}",
                "Cancel a task"
            ),
            BotCommand(
                f"{BotCommands.CancelAllCommand}",
                "Cancel all tasks added by you"
            ),
            BotCommand(
                f"{BotCommands.ListCommand}",
                "Search in Drive"
            ),
            BotCommand(
                f"{BotCommands.SearchCommand}",
                "Search in torrent"
            ),
            BotCommand(
                f"{BotCommands.UserSetCommand[0]}",
                "Users settings"
            ),
            BotCommand(
                f"{BotCommands.HelpCommand}",
                "Get detailed help"
            ),
        ])


async def get_telegraph_list(telegraph_content):
    path = [
        (
            await telegraph.create_page(
                title="𝚇𝚈𝚁𝙰𝙳 𝙳𝚁𝙸𝚅𝙴 𝚂𝙴𝙰𝚁𝙲𝙷",
                content=content
            )
        )["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await telegraph.edit_telegraph(
            path,
            telegraph_content
        )
    buttons = ButtonMaker()
    buttons.url_button(
        "🔎 ᴠɪᴇᴡ\nʀᴇꜱᴜʟᴛꜱ",
        f"https://telegra.ph/{path[0]}"
    )
    return buttons.build_menu(1)


def arg_parser(items, arg_base):
    if not items:
        return
    bool_arg_set = {
        "-b",
        "-e",
        "-z",
        "-s",
        "-j",
        "-d",
        "-sv",
        "-ss",
        "-f",
        "-fd",
        "-fu",
        "-sync",
        "-ml",
        "-doc",
        "-med"
    }
    t = len(items)
    i = 0
    arg_start = -1

    while i + 1 <= t:
        part = items[i]
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if (
                i + 1 == t
                and part in bool_arg_set
                or part in [
                    "-s",
                    "-j",
                    "-f",
                    "-fd",
                    "-fu",
                    "-sync",
                    "-ml",
                    "-doc",
                    "-med"
                ]
            ):
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j]
                    if item in arg_base:
                        if (
                            part in bool_arg_set
                            and not sub_list
                        ):
                            arg_base[part] = True
                        break
                    sub_list.append(item)
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1
    if (
        "link" in arg_base
        and items[0] not in arg_base
    ):
        link = []
        if arg_start == -1:
            link.extend(iter(items))
        else:
            link.extend(items[r] for r in range(arg_start))
        if link:
            arg_base["link"] = " ".join(link)


def get_size_bytes(size):
    size = size.lower()
    if size.endswith("mb"):
        size = size.split("mb")[0]
        size = int(float(size) * 1048576)
    elif size.endswith("gb"):
        size = size.split("gb")[0]
        size = int(float(size) * 1073741824)
    else:
        size = 0
    return size


async def get_content_type(url):
    try:
        async with AsyncClient() as client:
            response = await client.get(
                url,
                allow_redirects=True,
                verify=False
            )
            return response.headers.get("Content-Type")
    except:
        return None


def update_user_ldata(id_, key, value):
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(
            cmd,
            stdout=PIPE,
            stderr=PIPE
        )
    else:
        proc = await create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE
        )
    (
        stdout,
        stderr
    ) = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except:
        stderr = "Unable to decode the error!"
    return (
        stdout,
        stderr,
        proc.returncode
    )


def new_task(func):
    @wraps(func)
    async def wrapper(
        *args,
        **kwargs
    ):
        task = bot_loop.create_task(
            func(
                *args,
                **kwargs
            )
        )
        return task

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(
        func,
        *args,
        **kwargs
    )
    future = bot_loop.run_in_executor(
        THREAD_POOL,
        pfunc
    )
    return (
        await future
        if wait
        else future
    )


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(
        func(
            *args,
            **kwargs
        ),
        bot_loop
    )
    return (
        future.result()
        if wait
        else future
    )


def loop_thread(func):
    @wraps(func)
    def wrapper(
        *args,
        wait=False,
        **kwargs
    ):
        future = run_coroutine_threadsafe(
            func(
                *args,
                **kwargs
            ),
            bot_loop
        )
        return (
            future.result()
            if wait
            else future
        )

    return wrapper
