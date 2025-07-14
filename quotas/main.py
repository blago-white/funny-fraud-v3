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
    _QUOTA_REQ_TIME_FILE_PATH: str = Path(__file__).resolve().parent / '_tqwt.json'
    _QUOTA_FORMAT_KEYS: set[str] = {"quota_positive", "quota_created_at",
                                    "quota_providers_ips"}

    @property
    def validate_quota(self):
        quota = self._get_quota()

        if not quota.get("quota_positive"):
            raise QuotaFailError

        self._verif_quota_timestamp(
            quota_time=quota.get("quota_created_at"),
            positive=quota.get("quota_positive")
        )

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

        if int(new_quota.get("quota_created_at")) > int(
                self._get_quota().get("quota_created_at")):

            self._add_success_quota_request_time(req_time=time.time(),
                                                 positive=new_quota.get("quota_positive"))

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

    def _get_quota(self):
        try:
            with open(self._QUOTA_FILE_PATH) as file:
                quota_data = json.load(file)
        except Exception as e:
            raise QuotaFailError("Quota file undefined")

        return quota_data

    def _get_validated_quota(self, quota_json: dict):
        if not self._QUOTA_FORMAT_KEYS.issubset(set(quota_json.keys())):
            return

        return quota_json

    def _add_success_quota_request_time(self, req_time: int, positive: bool):
        data = self._get_requests_time_data()

        data["success_requests_timestamps"].update({f"{int(req_time)}": positive})
        data["magic_num"] += 1

        with open(self._QUOTA_REQ_TIME_FILE_PATH, "w") as file:
            json.dump(data, file)

    def _verif_quota_timestamp(self, quota_time: int, positive: bool):
        data = self._get_requests_time_data()

        for request_time in data.get("success_requests_timestamps"):
            if (abs(int(quota_time) - int(request_time)) <= 120
                ) and (
                    data.get("success_requests_timestamps")[request_time] is positive
            ):
                return True

        raise QuotaFailError()

    def _get_requests_time_data(self):
        with open(self._QUOTA_REQ_TIME_FILE_PATH) as file:
            data = json.load(file)

        if data.get("magic_num") - 2704 != len(
                data.get("success_requests_timestamps")):
            raise QuotaFailError()

        return data
