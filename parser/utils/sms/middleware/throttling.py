import threading
import time

# {"helper-sms": 0}


class SmsServiceThrottlingMiddleware:
    _THROTTLE_LISTS = {}

    @classmethod
    def clean_buffer(cls):
        cls._THROTTLE_LISTS = {}

    @classmethod
    def throttle(cls, rps: int, space: str):
        def wrapper(func):
            def wrapped(*args, **kwargs):
                try:
                    tasks_count = cls._THROTTLE_LISTS[space]
                except:
                    cls._THROTTLE_LISTS.setdefault(space, 0)

                    tasks_count = cls._THROTTLE_LISTS[space]

                cls._THROTTLE_LISTS[space] += 1

                time.sleep(tasks_count * (1/rps))

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    raise e
                finally:
                    if cls._THROTTLE_LISTS[space] == 1:
                        time.sleep(1 * (1/rps))

                    cls._THROTTLE_LISTS[space] -= 1

            return wrapped
        return wrapper


# @SmsServiceThrottlingMiddleware.throttle(rps=10, space="test")
# def test_req(n):
#     print(f"#{n} DELTA: {time.time() - START}")
#
#
# tasks = [threading.Thread(target=test_req, args=(i, )) for i in range(10)]
#
# for t in tasks:
#     t.start()
#
# print("WWWW")
# test_req(111)
# print("hhh")
