import os

from fake_useragent import UserAgent
from selenium.webdriver import ChromeOptions, Chrome
from selenium.webdriver.chrome.service import Service

from .gologin import GologinProfilesManager


class WebDriversService:
    def __init__(
            self, default_driver: Chrome = Chrome,
            default_opts_class: ChromeOptions = ChromeOptions,
            agent_service: UserAgent = UserAgent(
                os=["windows"],
                platforms=["pc"]
            ),
            gologin_manager: GologinProfilesManager = GologinProfilesManager(),
            driver_path: str = None):
        self._default_driver = default_driver
        self._default_opts_class = default_opts_class
        self._agent_service = agent_service
        self._driver_path = driver_path or os.environ.get("CHROME_DRIVER_PATH")
        self._gologin_manager = gologin_manager

    @property
    def gologin_manager(self) -> GologinProfilesManager:
        return self._gologin_manager

    def get_desctop(self, worker_id: str, proxy: str = None) -> tuple[str, Chrome]:
        return self.get(
            proxy=proxy,
            agent=type(self._agent_service)(
                os=["windows"],
                platforms=["pc"]
            ).random,
            worker_id=worker_id
        )

    def get(self, worker_id: str,
            proxy: str = None,
            agent: str = None) -> tuple[str, Chrome]:
        agent = agent or self._get_agent()

        return self._get_driver(
            opts=self._get_opts(
                agent=agent,
            ),
            agent=self._get_agent(),
            proxy=proxy,
            worker_id=worker_id
        )

    def _get_driver(self, opts: ChromeOptions,
                    agent: str,
                    proxy: str,
                    worker_id: str) -> tuple[str, Chrome]:
        pid = self._gologin_manager.get_profile_id(
            useragent=agent,
            proxy=proxy
        )

        return pid, self._default_driver(
            service=Service(executable_path=self._driver_path),
            options=self._gologin_manager.use_profile(
                pid=pid,
                driver_options=opts,
                worker_id=worker_id
            )
        )

    def _get_agent(self) -> str:
        return self._agent_service.random

    def _get_opts(
            self, agent: str,
            headless: bool = True):
        opts = self._default_opts_class()

        opts.add_argument("--window-size=2200,1000")

        if headless:
            opts.add_argument("--headless")

        opts.add_argument(f"user-agent={agent}")

        return opts
