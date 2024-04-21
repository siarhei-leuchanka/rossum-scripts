import rs_classes.async_request_client as async_client
import rs_classes.annotation as annotation
import json
import ipywidgets as widgets


async def search_with_query(
    client, query: json, allPages: bool = False, page_max=None
) -> dict:
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


async def get_annotations(
    client: async_client.AsyncRequestClient,
    token_input: str,
    url_input: widgets,
    query: dict,
    field_ids: list,
    bool_toggle: widgets,
    dropdown: widgets,
    page_max: int,
) -> dict:
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

    return annotations_collection
