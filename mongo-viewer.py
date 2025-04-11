import streamlit as st
import rs_classes.async_request_client as rs
import rs_classes.hooks as hs
import rs_functions.fetch_annotations_meta as fetch_annotations_meta
import rs_functions.fetch_annotation_content as fetch_annotation_content
import rs_functions.mongo_viewer_functions as mvf
import json
import asyncio

st.set_page_config(layout="wide")

# Streamlit app title
st.title("Mongo Debugger")

# Input fields for user configuration
TOKEN = st.text_input("Enter your API Token:", "")
BASE_URL = st.text_input("Enter the Base URL:", "https://us.app.rossum.ai/api")

client = rs.AsyncRequestClient(TOKEN, BASE_URL)

HOOK_TEMPLATE_ID = st.text_input("Hook Template ID:", "39")
BREAK_AFTER_SUCCESSFULL_RESULTS = st.checkbox("Break After Successful Results", True)
# IGNORE_CONDITIONS = st.checkbox("Ignore Conditions", True)
st.text("Ignore Conditions is not supported yet")
CHECK_QUEUE_IDS_LIMITATIONS = st.checkbox("Check Queue IDs Limitations", True)
# STAGED_PIPELINE = st.checkbox("Staged Pipeline", False)
st.text("Staged Pipeline is not supported yet")
STAGED_PIPELINE = False

TARGET_SCHEMA_ID = st.text_input("Target Schema ID:", "")
ANNOTATION_LIST = st.text_area("Annotation ID):", "").split(",")
st.text(
    "List of annotations is not supported yet. Please use single annotation id for now."
)


async def main():
    annotations_collection = await fetch_annotations_meta.get_annotation_meta(
        client, ANNOTATION_LIST
    )
    await fetch_annotation_content.get_annotation_content(
        client, annotations_collection
    )

    hooks = await mvf.collect_hooks_per_annotation(client, annotations_collection)

    mdh_hooks_per_annotation = mvf.find_hooks_to_analyse(
        annotations_collection, hooks, HOOK_TEMPLATE_ID
    )
    queries = mvf.extract_valid_queries_for_analysis(
        mdh_hooks_per_annotation, CHECK_QUEUE_IDS_LIMITATIONS, TARGET_SCHEMA_ID
    )

    for item in queries:
        result = {}
        query = item["query"]
        dataset = item["dataset"]
        signature = item["signature"]
        hook_obj = item["hook"]
        st.write(
            f"Analyzing: Dataset: {dataset}, Hook ID: {hook_obj.id}, Hook Name: {hook_obj.name}"
        )

        if query.get("find"):
            result = await client.data_storage_find(
                collectionName=dataset, query=query["find"]
            )
            mvf.visualize_result(query, result, signature)

        elif query.get("aggregate"):
            if STAGED_PIPELINE and len(query.get("aggregate")) > 1:
                pipeline = []

                for element in range(1, len(query["aggregate"])):
                    pipeline.append(query["aggregate"][0:-element])

                for stage in pipeline[::-1]:
                    pipeline_result = await client.data_storage_aggregate(
                        collectionName=dataset, pipeline=stage
                    )

                    st.text_area("Query:", json.dumps(stage, indent=4), height=250)
                    st.text_area(
                        "Result:",
                        json.dumps(pipeline_result["result"], indent=4)
                        if pipeline_result
                        else "No result",
                        height=250,
                    )

            else:
                result = await client.data_storage_aggregate(
                    collectionName=dataset, pipeline=query["aggregate"]
                )
                mvf.visualize_result(query, result, signature)

        else:
            st.write("No Find or Aggregate has been found or there is an empty query")

        if result.get("result") and BREAK_AFTER_SUCCESSFULL_RESULTS:
            st.write("The result above will be shown in the UI!")
            break


def run_async(func):
    return asyncio.run(func)


if st.button("Check Annotation"):
    run_async(main())
