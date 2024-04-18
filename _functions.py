# SL
import json
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import asyncio
from rs_classes import annotation as annotation
from rs_classes import async_request_client as async_client


async def search_with_query(client, query: json, allPages: bool = False, page_max = None) -> dict:
    annotation_library = {}
    next, response = await client._search(params=query)

    for result in response:
        annotation_library[result["id"]] = annotation.Annotation(result)

    page_count = 1

    if allPages:
        while next and (page_max is None or page_max + 1 > page_count):
            next, response = await client._search(params=query, next_page=next)
            for result in response:
                annotation_library[result["id"]] = annotation.Annotation(result)
            page_count += 1

    return annotation_library


def form_dataset(obj: annotation.Annotation, key: str, field_id: str) -> pd.DataFrame:
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
    client: async_client.AsyncRequestClient,
    token_input: str,
    url_input: widgets,
    query: dict,
    field_ids: list,
    bool_toggle: widgets,
    dropdown: widgets,
    page_max: int
) -> show_results:
    if dropdown.label == "prod-eu2":
        url = f"https://{url_input.value}{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")
    else:
        url = f"{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")

    # Collect annotations based on search query
    annotations_collection = await search_with_query(
        client, query, allPages=bool_toggle.value, page_max=page_max
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


async def pages_data(client, annotation_id):
    # get all pages data:
    pages_data = []
    next, response = await client._get_pages(annotation_id)
    pages_data.extend(response)

    while next:
        next, response = await client._get_pages(annotation_id, next_page=next)
        pages_data.extend(response)
    return pages_data


async def annotations_position_analysis(
    client: async_client.AsyncRequestClient,
    token_input: str,
    url_input: widgets,
    query: dict,
    bool_toggle: widgets,
    dropdown: widgets,
    page_max: int
):
    if dropdown.label == "prod-eu2":
        url = f"https://{url_input.value}{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")
    else:
        url = f"{dropdown.value}"
        client.reset_inputs(token_input, f"{url}/api")

    # Collect annotations based on search query
    annotations_collection = await search_with_query(
        client, query, allPages=bool_toggle.value, page_max=page_max
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

    # now creating a list of new coroutines to get page data
    pages_tasks = [pages_data(client, key) for key in annotations_collection.keys()]

    # Execute all annotation content fetching tasks concurrently
    annotation_pages = await asyncio.gather(*pages_tasks)

    # Update annotation objects with fetched pages
    for key, annotation_page in zip(annotations_collection.keys(), annotation_pages):
        obj = annotations_collection[key]
        obj.set_page_data = annotation_page

    return annotations_collection


def annotations_position_post_processing(
    annotations_collection, field_id, slicer_field_id
):
    output = pd.DataFrame()
    for key, obj in annotations_collection.items():
        df = pd.DataFrame()
        pages_df = pd.DataFrame(obj.page_data)
        positions = obj.get_positions(field_id)
        slicer = obj.find_by_schema_id(
            obj.content_data, slicer_field_id
        )  ##ugly hot fix for header only fields
        if slicer:
            slicer = slicer[0]
            slicer_value = slicer.get("content", [])["value"]
        else:
            slicer_value = "EMPTY SLICER"
        if positions[0].get("page", False):  # hot fix for header only fields
            positions_df = pd.DataFrame(positions)
            df = pd.merge(
                positions_df[["annotation_id", "page", "x1", "y1", "x2", "y2"]],
                pages_df[["page", "page_width", "page_height"]],
                on="page",
                how="left",
            )

        df["slicer"] = slicer_value
        output = pd.concat([output, df])

    # Convert coordinates to percentages
    # Calculate center of bounding box
    output["center_x"] = (output["x1"] + output["x2"]) / 2
    output["center_y"] = (output["y1"] + output["y2"]) / 2

    # Convert coordinates to relative percentages
    output["center_x_percent"] = output["center_x"] / output["page_width"] * 100
    output["center_y_percent"] = output["center_y"] / output["page_height"] * 100

    return output
