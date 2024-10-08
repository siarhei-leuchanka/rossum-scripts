import rs_classes.async_request_client as async_client
import rs_classes.annotation as annotation
import json
import asyncio


async def search_with_query(
    client: async_client, query: json, allPages: bool = False, page_max=None
) -> dict:
    annotation_library = {}
    next, response = await client._search(params=query)

    for result in response:
        annotation_library[result["id"]] = annotation.Annotation(result)

    page_count = 1

    if allPages:
        while next and (page_max is None or page_max + 1 > page_count):
            if page_count % 10 == 0:
                print("Sleeping - 2 seconds. ",page_count )
                await asyncio.sleep(2)
            if page_count % 100 == 0:
                print("Sleeping - 5 seconds. ",page_count )
                await asyncio.sleep(5)
            next, response = await client._search(params=query, next_page=next)
            for result in response:
                annotation_library[result["id"]] = annotation.Annotation(result)
            page_count += 1

    return annotation_library
