import json
import threading
import time

import requests
from pathlib import Path

from .exceptions import QuotaFailError


class QuotasManager:
    _active_quota: str
    _quota_updating_time: int

    _QUOTA_FILE_PATH: str = Path(__file__).resolve().parent / '_qwt.json'
    _QUOTA_FORMAT_KEYS: set[str] = {"quota_positive", "quota_created_at", "quota_providers_ips"}

    @property
    def validate_quota(self):
        if not self._get_quota().get("quota_positive"):
            raise QuotaFailError

        return True

    def start_quota_monitoring(self):
        monitoring_task = threading.Thread(target=self._quota_monitoring_task)

        monitoring_task.start()

    def _quota_monitoring_task(self):
        for _ in range(3):
            self._update_quota()

            time.sleep(5)

    def _update_quota(self):
        new_quota = self._get_updated_quota_data()

        if not new_quota:
            return

        if int(new_quota.get("quota_created_at")) > int(self._get_quota().get("quota_created_at")):
            self._save_new_quota(quota_data=new_quota)

    def _save_new_quota(self, quota_data: dict):
        with open(self._QUOTA_FILE_PATH, "w") as file:
            json.dump(quota_data, file)

    def _get_updated_quota_data(self):
        providers = self._get_quota().get("quota_providers_ips")

        for p in providers:
            try:
                response = requests.get(
                    url=f"http://{p}:27047/next-quota-data/",
                    timeout=10
                )
            except:
                continue

            if response.ok and (result := self._get_validated_quota(response.json())):
                return result

        return

    def _get_quota(self):
        try:
            with open(self._QUOTA_FILE_PATH, "r") as file:
                quota_data = json.load(file)
        except Exception as e:
            print(e, self._QUOTA_FILE_PATH)

            raise QuotaFailError("Quota file undefined")

        return quota_data

    def _get_validated_quota(self, quota_json: dict):
        if not self._QUOTA_FORMAT_KEYS.issubset(set(quota_json.keys())):
            return

        return quota_json
