from requests import request, exceptions

class HttpUtils:

    @staticmethod
    def request_api(method, url, data=None, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            res = request(
                method=method,
                url=url,
                headers=headers,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                params=data if method == "GET" else None
            )

            if res.status_code in (200, 201):
                return res.json()

        except exceptions.RequestException:
            return None

        return None
