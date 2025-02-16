# async_request_client.py

import aiohttp


class AsyncRequestClient:
    BASE_URL = "https://elis.rossum.ai/api"
    HEADERS = {
        "Content-Type": "application/json",
    }

    def __init__(self, token=None, domain=None):
        self._token = token
        self._base_url = domain or AsyncRequestClient.BASE_URL
        self.request_cache = {}

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, token):
        if token != "":
            self._token = token
        else:
            raise ValueError("Token can't be empty")

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, base_url):
        if base_url is not None:
            self._base_url = base_url
        else:
            raise ValueError("Select base_url!")

    # def reset_inputs(self, token, domain):
    #     self.token = token
    #     self.base_url = domain

    async def _make_request(
        self,
        method,
        endpoint=None,
        headers=None,
        data=None,
        json=None,
        files=None,
        cache_on=True,
        ready_url=None,
    ):
        url = ready_url or f"{self.base_url}/v1{endpoint}"
        headers = headers or AsyncRequestClient.HEADERS
        headers["Authorization"] = f"Bearer {self.token}"

        if self.request_cache.get(url, False) and cache_on:
            if self.request_cache[url]["json"] == json:
                print(f"Cached {url}")
                return self.request_cache[url]["response"]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    json=json,
                ) as response:
                    print(url, "  Request")
                    if response.status == 200 or response.status == 201:
                        self.request_cache[url] = {
                            "response": await response.json(),
                            "json": json,
                        }
                        return await response.json()
                    else:
                        print(response)
                        raise aiohttp.ClientResponseError
            except aiohttp.ClientResponseError as e:
                print("ClientResponseError occurred:", e)

    async def _get_annotation_content(self, annotation_id):
        endpoint = f"/annotations/{annotation_id}/content"
        response = await self._make_request("GET", endpoint, cache_on=True)
        return response

    async def _get_annotations_meta(self, annotation_list: str, next_page=None):
        endpoint = f"/annotations/?id={annotation_list}"
        response = await self._make_request(
            "GET", endpoint, cache_on=True, ready_url=next_page
        )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def _search(self, params=None, next_page=None) -> tuple:
        endpoint = "/annotations/search?page_size=100"
        response = await self._make_request(
            "POST", endpoint, json=params, cache_on=True, ready_url=next_page
        )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def _get_pages(self, annotation_id: str, next_page: str = None) -> tuple:
        endpoint = f"/pages?annotation={annotation_id}"
        response = await self._make_request(
            "GET", endpoint, cache_on=True, ready_url=next_page
        )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def _get_email(self, email_id: str) -> dict:
        endpoint = f"/emails/{email_id}"
        response = await self._make_request("GET", endpoint, cache_on=True)

        return response

    async def _get_queue(self, queue_id: str) -> dict:
        endpoint = f"/queues/{queue_id}"
        response = await self._make_request("GET", endpoint, cache_on=True)

        return response

    async def _get_hook(self, hook_id: str = None, hook_url: str = None) -> dict:
        if hook_url:
            response = await self._make_request(
                "GET", ready_url=hook_url, cache_on=True
            )
        else:
            endpoint = f"/hooks/{hook_id}"
            response = await self._make_request("GET", endpoint, cache_on=True)
        return response

    async def _get_all_users(self, next_page=False) -> dict:
        endpoint = f"/users"
        response = await self._make_request(
            "GET", endpoint, ready_url=next_page, cache_on=False
        )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def get_all_users(self) -> list:
        # get all pages data:
        pages_data = []
        next, response = await self._get_all_users()
        pages_data.extend(response)

        while next:
            next, response = await self._get_all_users(next_page=next)
            pages_data.extend(response)
        return pages_data

    async def create_new_user(self, data):
        endpoint = f"/users"
        response = await self._make_request("POST", endpoint, json=data, cache_on=False)

        return response

    async def reset_password(self, email):
        endpoint = f"/auth/password/reset"
        data = {"email": email}
        response = await self._make_request("POST", endpoint, json=data, cache_on=False)

        return response

    async def change_part_user(self, user_id, data):
        endpoint = f"/users/{user_id}"
        response = await self._make_request(
            "PATCH", endpoint, json=data, cache_on=False
        )

        return response

    async def _get_all_queues(self, next_page=False) -> dict:
        endpoint = f"/queues"
        response = await self._make_request(
            "GET", endpoint, ready_url=next_page, cache_on=False
        )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def get_all_queues(self) -> list:
        pages_data = []
        next, response = await self._get_all_queues()
        pages_data.extend(response)

        while next:
            next, response = await self._get_all_queues(next_page=next)
            pages_data.extend(response)
        return pages_data

    async def _get_groups(self) -> dict:
        endpoint = f"/groups"
        response = await self._make_request("GET", endpoint, cache_on=True)

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def get_all_groups(self, next_page=False) -> dict:
        pages_data = []
        next, response = await self._get_groups()

        pages_data.extend(response)

        while next:
            next, response = await self._get_groups(next_page=next)
            pages_data.extend(response)
        return pages_data

    async def data_storage_find(
        self,
        collectionName: str,
        query: dict,
        projection: dict = {},
        skip: int = 0,
        limit: int = 0,
        sort: dict = {},
    ):
        url = (
            "/".join(self._base_url.split("/")[:-1])
            + "/svc/data-storage/api/v1/data/find"
        )

        data = {
            "collectionName": collectionName,
            "query": query,
            "projection": projection,
            "skip": skip,
            "limit": limit,
            "sort": sort,
        }

        response = await self._make_request(
            "POST", ready_url=url, json=data, cache_on=False
        )

        return response

    async def data_storage_aggregate(
        self,
        collectionName: str,
        pipeline: list[dict],
        collation: dict = {},
        let: dict = {},
        options: dict = {},
    ):
        url = (
            "/".join(self._base_url.split("/")[:-1])
            + "/svc/data-storage/api/v1/data/aggregate"
        )
        data = {
            "collectionName": collectionName,
            "pipeline": pipeline,
            "collation": collation,
            "let": let,
            "options": options,
        }

        response = await self._make_request(
            "POST", ready_url=url, json=data, cache_on=False
        )

        return response
