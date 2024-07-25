import rs_classes.async_request_client as async_client
from rs_functions.gather_decorator import gather_throttled


async def get_annotation_meta(
    client: async_client.AsyncRequestClient,
    annotations_collection: dict,
) -> dict:
    # Create a list of coroutines for fetching annotation content
    annotation_tasks = [
        client._get_annotation_meta(key) for key in annotations_collection.keys()
    ]

    # Home baked primitive throttling
    annotation_meta = await gather_throttled(
        tasks=annotation_tasks, sleep_limit=100, sleep_time=1
    )

    # Update annotation objects with fetched content
    for key, annotation_meta in zip(
        annotations_collection.keys(), annotation_meta
    ):
        obj = annotations_collection[key]
        content = annotation_meta        
        obj.set_meta(content)

    return annotations_collection
