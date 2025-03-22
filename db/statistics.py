import datetime
import pytz

from .base import BaseRedisService


class LeadsGenerationStatisticsService(BaseRedisService):
    def add(self, session_id: int, link: str, count_leads: int) -> bool:
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))

        date_key = f"daystat:{today_date.day}:{today_date.month}"

        try:
            current_data = str(
                self._conn.get(date_key)
            ).decode()
        except:
            current_data = ""

        if f"SSID{session_id}" in current_data:
            return True

        if not current_data:
            current_data = f"{link}#{count_leads}#SSID{session_id}"
        else:
            current_data += f"@{link}#{count_leads}#SSID{session_id}"

        self._conn.set(date_key, current_data)

        return True

    def get_today(self) -> tuple[dict, int]:
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))

        date_key = f"daystat:{today_date.day}:{today_date.month}"

        try:
            current_data = str(
                self._conn.get(date_key)
            ).decode()
        except:
            return {}, 0

        statistics_for_links, total_count = {}, 0

        for i in current_data.split("@"):
            row_params = i.split("#")

            link, count = row_params[0], int(row_params[1])

            total_count += count
            statistics_for_links.update({
                link: count
            })

        return statistics_for_links, total_count
