import rs_classes.async_request_client as async_client
from rs_functions.gather_decorator import gather_throttled


async def get_email_content(
    client: async_client.AsyncRequestClient,
    annotations_collection: dict,
) -> dict:
    # Create a list of coroutines for fetching annotation content
    annotation_tasks = {} 
    for annotation in annotations_collection:
          
        for email_id in annotation.related_email_ids:
            task = client._get_email(email_id)
            annotation_tasks[(annotation,email_id)] = task


    # Home baked primitive throttling
    annotation_related_emails = await gather_throttled(
        tasks=annotation_tasks.values(), sleep_limit=100, sleep_time=1
    )

    for (annotation, email_id) in annotation_tasks.keys():
        for email_content in annotation_related_emails:            
            if int(email_content["id"]) == int(email_id):
                annotation.related_emails = email_content
            
    return annotation_related_emails
    
    