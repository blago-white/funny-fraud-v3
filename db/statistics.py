import datetime
import pytz

from .base import BaseRedisService


class LeadsGenerationStatisticsService(BaseRedisService):
    def add_sms_delta_balance(self, session_id: int, delta: float):
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))

        try:
            current_delta = self._conn.get(
                f"balancestat:{today_date.day}:{today_date.month}"
            ).decode()
        except:
            current_delta = "0|"

        all_time_delta, sids = current_delta.split("|")

        if f"SSID{session_id}" in sids:
            return True

        all_time_delta = str(float(all_time_delta) + delta)

        sids += f"SSID{session_id}"

        self._conn.set(
            f"balancestat:{today_date.day}:{today_date.month}",
            f"{all_time_delta}|{sids}"
        )

    def get_today_sms_delta_balance(self):
        try:
            current_delta = self._conn.get(
                f"balancestat:{today_date.day}:{today_date.month}"
            ).decode().split("|")[0]

            return float(current_delta)
        except:
            return 0

    def add_leads_count(self, session_id: int, link: str, count_leads: int) -> bool:
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))
        date_key = f"daystat:{today_date.day}:{today_date.month}"

        aff_id = self._extract_aff_id(link=link)

        try:
            current_data = self._conn.get(date_key).decode()
        except:
            current_data = ""

        if f"SSID{session_id}{aff_id}" in current_data:
            return True

        data = f"{link}#{count_leads}#SSID{session_id}{aff_id}"

        if len(current_data) >= 1:
            data = "@" + data

        self._conn.set(date_key, current_data + data)

        return True

    def get_today_leads_count(self) -> tuple[dict, int]:
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))

        date_key = f"daystat:{today_date.day}:{today_date.month}"

        try:
            current_data = self._conn.get(date_key).decode()
        except Exception as e:
            print(f"ERROR GET TODAY STATS: {e}")
            return {}, 0

        print("FFFFFFFFFFFFUCCCL", current_data)

        statistics_for_links, total_count = {}, 0

        if not current_data:
            return statistics_for_links, total_count

        for i in current_data.split("@"):
            row_params = i.split("#")

            try:
                link, count = row_params[0], int(row_params[1])
            except:
                continue

            total_count += count

            statistics_for_links.update({
                link: count + statistics_for_links.get(link, 0)
            })

        return statistics_for_links, total_count

    @staticmethod
    def _extract_aff_id(link: str) -> str:
        return "".join([i for i in link if i.isdigit()][:6])
