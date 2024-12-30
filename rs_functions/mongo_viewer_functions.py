# mongo_viewer_functions.py
import rs_classes.async_request_client as async_client
import rs_classes.hooks as hs 
from rs_functions.gather_decorator import gather_throttled 
import re


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

def find_and_replace_placeholder(json_obj, content:str):    
    if isinstance(json_obj, str):                
        # Match the placeholder pattern
        field_id = re.match(r"({(\s*[\w-]+(\s*\|\s*[^}]*)?)})", json_obj)
        field_id_regex = re.search(r"\{[^|{}]+\s*\|\s*regex\}", json_obj)
                
        if field_id:            
            replacement_value = find_by_schema_id(content, json_obj.strip("{}"))[0]["content"]["value"]
        
            # Replace the value in place (directly modify the input string in the JSON structure)
            return replacement_value

        elif field_id_regex:            
            match = re.match(r"\{([\w,\d]+)", field_id_regex.group(0))
            replacement_value = find_by_schema_id(content, match.group(1))[0]["content"]["value"]        

            return re.sub(r"\{[^|{}]+\s*\|\s*regex\}", replacement_value, json_obj)
        
    elif isinstance(json_obj, list):
        for i, item in enumerate(json_obj):            
            json_obj[i] = find_and_replace_placeholder(item, content)
        
    elif isinstance(json_obj, dict):
        for key, value in json_obj.items():
            json_obj[key] = find_and_replace_placeholder(value, content)

    return json_obj


def find_by_schema_id(content: list, schema_id: str) -> list:
    """
    Return datapoints matching a schema id.
    :param content: annotation content tree (see https://api.elis.rossum.ai/docs/#annotation-data)
    :param schema_id: field's ID as defined in the extraction schema(see https://api.elis.rossum.ai/docs/#document-schema)
    :return: the list of datapoints matching the schema ID
    """
    accumulator = []
    for node in content:
        if node["schema_id"] == schema_id:
            accumulator.append(node)
        elif "children" in node:
            accumulator.extend(find_by_schema_id(node["children"], schema_id))

    return accumulator