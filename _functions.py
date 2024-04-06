# SL
import json
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import asyncio
import aiohttp


class Annotation:
    def __init__(self, metadata: json) -> None:
        self.metadata = metadata
        self.id = metadata.get("id", "na")
        self.queue = metadata.get("queue", "na").split("/")[-1]
        self.schema = metadata.get("schema", "na").split("/")[-1]

    def set_content(self, annotation: list) -> None:
        self.content_data = annotation

    def find_by_schema_id(self, content, schema_id: str):
        """
        Return all datapoints matching a schema id.
        :param content: annotation content tree
        :param schema_id: f
        :return: the list of datapoints matching the schema ID
        """
        accumulator = []
        for node in content:
            if node["schema_id"] == schema_id:
                accumulator.append(node)
            elif "children" in node:
                accumulator.extend(self.find_by_schema_id(node["children"], schema_id))

        return accumulator


class AsyncRequestClient:
    BASE_URL = "https://elis.rossum.ai/api"
    HEADERS = {
        "Content-Type": "application/json",
    }

    def __init__(self, token, domain=None):
        self.token = token
        self.base_url = domain or AsyncRequestClient.BASE_URL
        self.request_cache = {}

    def reset_inputs(self, token, domain):
        self.token = token
        self.base_url = domain

    async def _make_request(
        self,
        method,
        endpoint,
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
                    if response.status == 200:
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

    async def _search(self, params=None, next_page=None):
        if next_page:
            response = await self._make_request(
                "POST", self.endpoint, json=params, cache_on=True, ready_url=next_page
            )
        else:
            self.endpoint = "/annotations/search"
            response = await self._make_request(
                "POST", self.endpoint, json=params, cache_on=True
            )

        pagination = response["pagination"]
        next_page = pagination.get("next", False)

        return next_page, response["results"]

    async def search_with_query(self, query: json, allPages: bool = False) -> dict:
        annotation_library = {}
        next, response = await self._search(params=query)

        for result in response:
            annotation_library[result["id"]] = Annotation(result)

        if allPages:
            while next:
                next, response = await self._search(params=query, next_page=next)
                for result in response:
                    annotation_library[result["id"]] = Annotation(result)

        return annotation_library


def form_dataset(obj: Annotation, key: str, field_id: str) -> pd.DataFrame:
    temp_list = []
    datapoints = obj.find_by_schema_id(obj.content_data, field_id)
    if datapoints:
        for datapoint in datapoints:
            content_value = datapoint["content"]["value"]
            temp_list.append({"IDs": key, field_id: content_value})
        temp_df = pd.DataFrame(temp_list)
        temp_df.set_index("IDs", inplace=True)
        return temp_df
    # if no datapoints return empty df
    return pd.DataFrame()


def show_results(
    field_ids: list, annotations_collection: dict, base_url: str
) -> display:
    output = pd.DataFrame()
    for key, obj in annotations_collection.items():
        temp_merged_df = pd.DataFrame([{"IDs": key, "Address": f"{base_url}/{key}"}])
        temp_merged_df.set_index("IDs", inplace=True)
        for field_id in field_ids:
            temp_merged_df = temp_merged_df.merge(
                form_dataset(obj, key, field_id),
                how="outer",
                left_index=True,
                right_index=True,
            )
        output = pd.concat([output, temp_merged_df])

    def make_clickable(url):
        return f'<a href="{url}" target="_blank">link</a>'

    styled_output = output.style.format({"Address": make_clickable})
    return display(styled_output)


# Function to create input widgets for a given set number
def create_input_widgets() -> widgets:
    url_input = widgets.Textarea(value="", description="Custom Domain:")
    bool_toggle = widgets.ToggleButtons(
        options=[True, False],
        description="Load all pages of annotations:",
        tooltips=["True", "False"],
        value=False,  # Default value
    )

    options_with_labels = {
        "prod-eu": "https://elis.rossum.ai",
        "prod-jp": "https://shared-jp.app.rossum.ai",
        "prod-eu2": ".rossum.app",
        "prod-us": "https://us.app.rossum.ai",
    }
    dropdown = widgets.Dropdown(options=options_with_labels, description="Environment:")

    return url_input, bool_toggle, dropdown


async def process_annotations(
    client: AsyncRequestClient,
    token_input: str,
    url_input: widgets,
    query: dict,
    field_ids: list,
    bool_toggle: widgets,
    dropdown: widgets,
) -> show_results:
    if dropdown.label == "prod-eu2":
        url = f"https://{url_input.value}{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")
    else:
        url = f"{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")

    # Collect annotations based on search query
    annotations_collection = await client.search_with_query(
        query, allPages=bool_toggle.value
    )

    # Create a list of coroutines for fetching annotation content
    annotation_tasks = [
        client._get_annotation_content(key) for key in annotations_collection.keys()
    ]

    # Execute all annotation content fetching tasks concurrently
    annotation_contents = await asyncio.gather(*annotation_tasks)

    # Update annotation objects with fetched content
    for key, annotation_content in zip(
        annotations_collection.keys(), annotation_contents
    ):
        obj = annotations_collection[key]
        content = annotation_content
        content = content["content"]
        obj.set_content(content)

    return show_results(field_ids, annotations_collection, base_url=f"{url}/document")
