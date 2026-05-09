from datetime import datetime, timedelta

class TimeUtils:

    @staticmethod
    def now_str():
        return datetime.now().strftime("%d/%m/%y %I:%M:%S %p")

    @staticmethod
    def elapsed(start, end):
        return str(timedelta(seconds=(end - start)))
