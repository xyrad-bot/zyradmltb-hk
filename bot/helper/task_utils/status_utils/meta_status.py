from bot import (
    LOGGER,
    pkg_info,
    subprocess_lock
)
from ...ext_utils.status_utils import (
    get_readable_file_size,
    MirrorStatus
)
from subprocess import run as frun
from time import time


class MetaStatus:
    def __init__(
            self,
            listener,
            gid
        ):
        self.listener = listener
        self._gid = gid
        self._size = self.listener.size
        self._start_time = time()
        self._proccessed_bytes = 0
        self.engine = f"FFmpeg v{self._eng_ver()}"

    def _eng_ver(self):
        _engine = frun(
            [
                pkg_info["pkgs"][2],
                "-version"
            ],
            capture_output=True,
            text=True
        )
        return _engine.stdout.split("\n")[0].split(" ")[2].split("-")[0]

    def gid(self):
        return self._gid

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def status(self):
        return MirrorStatus.STATUS_METADATA

    def speed(self):
        return "0B/s"

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling metadata editor: {self.listener.name}")
        self.listener.is_cancelled = True
        async with subprocess_lock:
            if (
                self.listener.suproc is not None
                and self.listener.suproc.returncode is None
            ):
                self.listener.suproc.kill()
        await self.listener.on_upload_error("Metadata editing stopped by user!")
