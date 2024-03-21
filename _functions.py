# SL
import json
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import asyncio
import aiohttp

class Annotation():
    def __init__(self, metadata:json) -> None:
        self.metadata = metadata
        self.id = metadata.get("id", "na")
        self.queue = metadata.get("queue", "na").split("/")[-1]
        self.schema = metadata.get("schema", "na").split("/")[-1]

    def set_content(self, annotation:list) -> None:
        self.content_data = annotation


class AsyncRequestClient():    
    
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


    async def _make_request(self, method, endpoint, headers=None, data=None, json=None, files=None, cache_on=True, ready_url=None):
        url = ready_url or  f"{self.base_url}/v1{endpoint}"
        headers = headers or AsyncRequestClient.HEADERS
        headers["Authorization"] = f"Bearer {self.token}"
        
        if self.request_cache.get(url, False) and cache_on:
            if self.request_cache[url]["json"] == json:
                print(f"Cached {url}")
                return self.request_cache[url]["response"]
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=headers, data=data, json=json,) as response:
                    print(url, "  Request")
                    if response.status == 200:
                        self.request_cache[url] = {
                            "response": await response.json(),
                            "json": json                       
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
            response = await self._make_request("POST", self.endpoint, json=params, cache_on=True, ready_url=next_page)
        else: 
            self.endpoint = f"/annotations/search"         
            response = await self._make_request("POST", self.endpoint, json=params, cache_on=True)
                
        pagination = response["pagination"]
        next_page = pagination.get("next", False)                
        
        return next_page, response["results"]
    
    async def search_with_query(self, query:json ,allPages:bool = False)->dict:                
        annotation_library = {}        
        next, response  = await self._search(params=query)     
        
        for result in response:
            annotation_library[result["id"]] = Annotation(result)
        
        if allPages:
            while next:         
                next,response = await self._search(params=query, next_page=next)            
                for result in response:
                    annotation_library[result["id"]] = Annotation(result)
                                    
        return annotation_library


def find_by_schema_id(content, schema_id: str):
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
            accumulator.extend(find_by_schema_id(node["children"], schema_id))

    return accumulator


def show_results(field_id, annotations_collection, base_url):
    df_list = []
    for key in annotations_collection.keys():
        annotation = annotations_collection[key].content_data
      
        datapoints = find_by_schema_id(annotation, field_id)
        if datapoints:
            for datapoint in datapoints:
                time_spent_overall = datapoint["time_spent_overall"]
                validation_sources = datapoint["validation_sources"]
                content_value = datapoint["content"]["value"]
                
                df_list.append({"IDs":f"{base_url}/{key}", "value":content_value, "validation_sources":validation_sources, "time_spent_overall":time_spent_overall})    

    output = pd.DataFrame(df_list)
    def make_clickable(url):
        return f'<a href="{url}" target="_blank">{url}</a>'
    styled_output = output.style.format({'IDs': make_clickable})
    
    display(styled_output)


# Function to create input widgets for a given set number
def create_input_widgets():      
    token_input = widgets.Textarea(value="", description=f"TOKEN:")
    url_input = widgets.Textarea(value="", description=f"Custom Domain:")    
    field_id = widgets.Textarea(value="document_id", description = "Field ID to check")
    query = widgets.Textarea(
                    value= '{\n    "query": {\n        "$and": [\n            {\n                "queue": {\n                    "$in": [\n                        "https://elis.rossum.ai/api/v1/queues/1813424",\n                        "https://elis.rossum.ai/api/v1/queues/1813427",\n                        "https://elis.rossum.ai/api/v1/queues/1851757"\n                    ]\n                }\n            },\n            {\n                "field.document_id.string": {\n                    "$emptyOrMissing": false\n                }\n            },\n            {\n                "status": {\n                    "$in": [\n                        "confirmed",\n                        "exported"\n                    ]\n                }\n            }\n        ]\n    }\n}',
                    description='Filter Query',
                    layout={'width': '80%', 'height': '500px'}  # Set width to 80% of the available space
                        )
    bool_toggle = widgets.ToggleButtons(
                    options=[True, False],
                    description='Load all pages of annotations:',
                    button_style='info', # 'success', 'info', 'warning', 'danger' or ''
                    tooltips=['True', 'False'],
                    value=False # Default value
                )
    
    options_with_labels = {'prod-eu': 'https://elis.rossum.ai', 'prod-jp': 'https://shared-jp.app.rossum.ai', 
                           'prod-eu2': f'.rossum.app', 'prod-us': 'https://us.app.rossum.ai'}
    dropdown = widgets.Dropdown(
                options=options_with_labels,
                description='Environment:'
                )
    
    # confirm_button = widgets.Button(description="Start")

    return token_input, url_input, query, field_id, bool_toggle, dropdown


async def process_annotations(client, token_input, url_input, query, field_id, bool_toggle, dropdown):
    query_string = query.value.replace("\n", "")
    
    if dropdown.label == "prod-eu2":
        url = f'https://{url_input.value}{dropdown.value}/api'
        print(url)
        client.reset_inputs(token_input.value, url)
    else:
        url = f'{dropdown.value}'
        client.reset_inputs(token_input.value, f'{url}/api')

    annotations_collection = await client.search_with_query(json.loads(query_string), allPages=bool_toggle.value)

    # Create a list of coroutines for fetching annotation content
    annotation_tasks = [client._get_annotation_content(key) for key in annotations_collection.keys()]

    # Execute all annotation content fetching tasks concurrently
    annotation_contents = await asyncio.gather(*annotation_tasks)

    # Update annotation objects with fetched content
    for key, annotation_content in zip(annotations_collection.keys(), annotation_contents):
        obj = annotations_collection[key]
        content = annotation_content
        content= content["content"]
        obj.set_content(content)

    show_results(field_id.value, annotations_collection, base_url=f'{url}/document')
