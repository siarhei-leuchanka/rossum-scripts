# mongo_viewer_functions.py
import rs_classes.async_request_client as async_client
import rs_classes.hooks as hs 
from rs_functions.gather_decorator import gather_throttled 


async def collect_hooks_per_annotation(client:async_client, annotations_collection):

    print("\033[33mCollecting Hooks\033[0m")
    hooks_list = []
    for annotation_id, annotation in annotations_collection.items():    
        queue_data = await client._get_queue(annotation.queue)
        annotation.related_hooks = queue_data.get("hooks", [])
        hooks_list.extend(annotation.related_hooks)

    hooks = hs.HookManager()

    hooks_tasks = [client._get_hook(hook_url=hook) for hook in list(set(hooks_list))]

    # Home baked primitive throttling
    hooks_responses = await gather_throttled(
        tasks=hooks_tasks, sleep_limit=100, sleep_time=1
    )
    for hook_data in hooks_responses:
        hooks.add_hook(hook_data)

    print("\033[32mHooks are created and added to annotations' metadata\033[0m")

    return hooks