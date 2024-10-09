import rs_classes.async_request_client as async_client
import rs_classes.annotation as annotation
import asyncio


async def get_annotation_meta(
    client: async_client.AsyncRequestClient,
    annotation_list: dict,
) -> dict:
    ids = ",".join(annotation_list)

    annotation_collection = {}
    next, response = await client._get_annotations_meta(ids)

    for result in response:
        annotation_collection[result["id"]] = annotation.Annotation(result)

    page_count = 1

    while next:
        if page_count % 10 == 0:
            print("Sleeping - 2 seconds. ", page_count)
            await asyncio.sleep(2)
        if page_count % 100 == 0:
            print("Sleeping - 5 seconds. ", page_count)
            await asyncio.sleep(5)
        next, response = await client._get_annotations_meta(ids, next_page=next)
        for result in response:
            annotation_collection[result["id"]] = annotation.Annotation(result)
        page_count += 1

    return annotation_collection
