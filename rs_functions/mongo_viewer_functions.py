# mongo_viewer_functions.py
import rs_classes.async_request_client as async_client
import rs_classes.hooks as hs
from rs_functions.gather_decorator import gather_throttled
import re
import copy
import streamlit as st
import json

# from streamlit_ace import st_ace


async def collect_hooks_per_annotation(client: async_client, annotations_collection):
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


def find_and_replace_placeholder(json_obj, content: str):
    """

    TODO: add line items support
    TODO: consider split filter
    TODO: consider replacing all regex based fields not only the first one.
    """
    if isinstance(json_obj, str):
        # Match the placeholder pattern
        field_id = re.findall(r"({(\s*[\w-]+(\s*\|\s*[^}]*)?)})", json_obj)
        field_id_regex = re.search(r"\{[^|{}]+\s*\|\s*regex|\s*split|\s*re\}", json_obj)
        if field_id and not field_id_regex:
            for replacement in field_id:
                replacement_value = find_by_schema_id(
                    content, replacement[1].strip(" ").strip("{}")
                )
                if len(replacement_value) == 1:
                    item = replacement_value[0]["content"]["value"]
                    if item:
                        json_obj = re.sub(replacement[0], item, json_obj)
                    else:
                        json_obj = re.sub(replacement[0], " ", json_obj)  # terrible fix
                else:
                    raise IndexError("Multivalue fields are not supported.")
            return json_obj

        elif field_id_regex:
            match = re.match(r"\{([\w,\d]+)", json_obj)
            replacement_value = find_by_schema_id(content, match.group(1))[0][
                "content"
            ]["value"]
            escaped_replacement_value = re.escape(replacement_value)
            print("here", json_obj, escaped_replacement_value)
            obj_list = []
            if "split" in json_obj:
                obj_list.append(replacement_value)
                json_obj = obj_list  # another terrible fix
            else:
                json_obj = escaped_replacement_value
            # return re.sub(r".*", escaped_replacement_value, json_obj, flags=re.DOTALL)

            return json_obj

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


def find_hooks_to_analyse(
    annotations_collection: dict, hooks, hook_template_id: str
) -> list:
    hooks_to_analyse = []
    for annotation_id, annotation in annotations_collection.items():
        print(f"\033[33m Analysing annotation: {annotation_id}.. \033[0m")
        for hook in annotation.related_hooks:
            hook_obj = hooks.get_hook(hook.split("/")[-1])
            if not hook_obj.hook_template:
                continue
            if hook_obj.hook_template.split("/")[-1] == hook_template_id:
                hooks_to_analyse.append((hook_obj, annotation))
    return hooks_to_analyse


def extract_valid_queries_for_analysis(
    mdh_hooks_per_annotation, CHECK_QUEUE_IDS_LIMITATIONS, TARGET_SCHEMA_ID
):
    queries = []
    for hook_obj, annotation in mdh_hooks_per_annotation:
        configuration_number = 1
        for configuration in hook_obj.settings.get("configurations", None):
            additional_mappings = next(
                (
                    mapping
                    for mapping in configuration.get("additional_mappings", [])
                    if mapping["target_schema_id"] == TARGET_SCHEMA_ID
                ),
                {},
            )
            queue_ids = configuration.get("queue_ids", [])
            excluded_queue_ids = configuration.get("excluded_queue_ids", [])
            # TODO: check conditiion.

            if (
                CHECK_QUEUE_IDS_LIMITATIONS
                and queue_ids
                and (
                    int(annotation.queue) not in queue_ids
                    or int(annotation.queue) in excluded_queue_ids
                )
            ):
                continue

            if TARGET_SCHEMA_ID == configuration["mapping"][
                "target_schema_id"
            ] or TARGET_SCHEMA_ID == additional_mappings.get("target_schema_id"):
                dataset = configuration["source"]["dataset"]
                dataset_key = (
                    additional_mappings.get("dataset_key")
                    or configuration["mapping"]["dataset_key"]
                )
                print(
                    f"\033[36m Hook {hook_obj.id} - {hook_obj.name} has configuration #:{configuration_number} with target_schema_id = {TARGET_SCHEMA_ID} in the annotation: {annotation.id}, that is mapped to {dataset_key} key in the dataset {dataset}.\033[0m"
                )

                for raw_query in configuration["source"]["queries"]:
                    query = copy.deepcopy(raw_query)
                    find_and_replace_placeholder(query, annotation.annotation_content)
                    signature = f"{annotation.id}-{hook_obj.id}-{configuration_number}"
                    queries.append(
                        {
                            "signature": signature,
                            "query": query,
                            "dataset": dataset,
                            "dataset_key": dataset_key,
                            "hook": hook_obj,
                            "annotation": annotation,
                        }
                    )
                    configuration_number += 1
    return queries


def visualize_result(query, result, title_text, col1_expanded = True, col2_expanded=True):
    # Title
    st.markdown(f"### {title_text}")

    # Layout with two columns
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.expander("Reveal:"):
            st.markdown("#### Query")
            st.json(query, expanded=col1_expanded)

    with col2:
        results_number = len(result.get("result", 0))
        st.write(f"Results found: {results_number}")
        st.markdown("#### Result")
        if result and "result" in result and results_number > 0:
            st.json(result["result"], expanded=col2_expanded)
        else:
            st.write("No result")

def prepare_pipeline(query):
    pipeline = []

    for element in range(1, len(query["aggregate"])):
        pipeline.append(query["aggregate"][0:-element])
    
    pipeline.reverse()
    
    return pipeline