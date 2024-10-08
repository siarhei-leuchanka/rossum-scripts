import rs_classes.async_request_client as async_client
from rs_functions.gather_decorator import gather_throttled


async def pages_data(client: async_client.AsyncRequestClient, annotation_id) -> list:
    # get all pages data:
    pages_data = []
    next, response = await client._get_pages(annotation_id)
    pages_data.extend(response)

    while next:
        next, response = await client._get_pages(annotation_id, next_page=next)
        pages_data.extend(response)
    return pages_data


async def get_annotations_page(
    client: async_client.AsyncRequestClient, annotations_collection: dict
) -> None:
    # now creating a list of new coroutines to get page data
    pages_tasks = [pages_data(client, key) for key in annotations_collection.keys()]

    # Home baked primitive throttling
    annotation_pages = await gather_throttled(
        tasks=pages_tasks, sleep_limit=100, sleep_time=1
    )

    # Update annotation objects with fetched pages
    for key, annotation_page in zip(annotations_collection.keys(), annotation_pages):
        obj = annotations_collection[key]
        obj.page_data = annotation_page

