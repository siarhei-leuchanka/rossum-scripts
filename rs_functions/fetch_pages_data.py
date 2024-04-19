import rs_classes.async_request_client as async_client
import asyncio


async def pages_data(client, annotation_id):
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
):
    # now creating a list of new coroutines to get page data
    pages_tasks = [pages_data(client, key) for key in annotations_collection.keys()]

    # Execute all annotation content fetching tasks concurrently
    annotation_pages = await asyncio.gather(*pages_tasks)

    # Update annotation objects with fetched pages
    for key, annotation_page in zip(annotations_collection.keys(), annotation_pages):
        obj = annotations_collection[key]
        obj.set_page_data = annotation_page

    return annotations_collection
