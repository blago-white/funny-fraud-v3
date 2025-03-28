import datetime
import pytz

from .base import BaseRedisService


class LeadsGenerationStatisticsService(BaseRedisService):
    def add(self, session_id: int, link: str, count_leads: int) -> bool:
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

    def get_today(self) -> tuple[dict, int]:
        today_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))

        date_key = f"daystat:{today_date.day}:{today_date.month}"

        try:
            current_data = self._conn.get(date_key).decode()
        except Exception as e:
            print(f"ERROR GET TODAY STATS: {e}")
            return {}, 0

        print("FFFFFFFFFFFFUCCCL", current_data)

        statistics_for_links, total_count = {}, 0

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
