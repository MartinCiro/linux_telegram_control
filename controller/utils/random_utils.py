from random import uniform, choice
from time import sleep

class RandomUtils:

    @staticmethod
    def delay(min_s=1.0, max_s=3.0):
        sleep(uniform(min_s, max_s))

    @staticmethod
    def random_user_agent():
        return choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
        ])
