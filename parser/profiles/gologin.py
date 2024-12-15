import random
import string

from gologin import GoLogin
from selenium.webdriver.chrome.options import Options

from db.gologin import GologinApikeysRepository


class GologinProfilesManager:
    _TOKEN = None
    _gologin_repository: GologinApikeysRepository = GologinApikeysRepository()

    def __init__(self, token: str = None):
        self._TOKEN = token or self._gologin_repository.get_current()

        self._manager = GoLogin(options={
            "token": self._TOKEN,
            "spawn_browser": False
        })

    def use_profile(self, driver_options: Options,
                    pid: str,
                    worker_id: int):
        debugger_address = self._get_gologin_debugger(
            pid=pid,
            worker_id=worker_id
        )

        driver_options.add_experimental_option(
            "debuggerAddress", debugger_address
        )

        return driver_options

    def get_profile_id(self, useragent: str, proxy: str) -> str:
        pid = self._manager.create({
            "name": "".join(
                [random.choice(string.ascii_lowercase) for _ in range(10)]
            ),
            "os": 'win',
            "navigator": {
                "language": 'ru',
                "userAgent": useragent,
                "resolution": '1024x768',
                "platform": 'win',
            },
            'proxyEnabled': True,
            'proxy': {
                'mode': 'gologin',
                'host': proxy.split("@")[1].split(":")[0],
                'port': proxy.split("@")[1].split(":")[-1],
                'username': proxy.split(":")[0],
                'password': proxy.split("@")[0].split(":")[-1],
            },
            "webRTC": {
                "mode": "alerted",
                "enabled": True,
            },
        })

        return pid

    def delete_profile(self, pid: str):
        self._manager.delete(
            profile_id=pid
        )

    def close(self):
        self._manager.stop()

    def _get_gologin_debugger(self, pid: str, worker_id: int) -> str:
        print(f"USED PORT: {10000+(worker_id%10000)}")
        return GoLogin({
            "token": self._TOKEN,
            "profile_id": pid,
            "port": 10000+(worker_id%10000)
        }).start()
