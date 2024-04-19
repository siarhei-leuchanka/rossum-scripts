import rs_classes.async_request_client as async_client
import asyncio


async def get_annotation_content(
    client: async_client.AsyncRequestClient,
    annotations_collection: dict,
) -> dict:
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

    return annotations_collection
