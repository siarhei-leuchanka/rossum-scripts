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
st.title("Mongo Debugger for Rossum Master Data Hub Extension (MDH)")
st.warning(
    "⚠️ Disclaimer: This application does not gurantee correctness of the results. Use at your own risk. If you see any issues, please report them to author. Fixes are not guranteed."
)
st.warning(
    "Current version does not support line items. The implementation of 'filters' like ' | re' or ' | regex' are suppoorted naively by re.escape() function. In case regex field has multiple placeholders only the first one will be taken into cosideration. 'split' filter is not supported."
)
st.info(
    "ℹ️ The implementation does not copy the original source code of the extension. The extension is treated as 'black box' and therefore can provide different results. The idea is to debug queries that are added in (MDH) extension."
)


# Input fields for user configuration
TOKEN = st.text_input("Enter your API Token:", "")
CLUSTER_URL = st.selectbox(
    "Select the Base URL:",
    [
        "https://elis.rossum.ai/api",
        "https://shared-jp.app.rossum.ai/api",
        "https://us.app.rossum.ai/api",
    ],
    index=2,
)
DOMAIN_URL = st.text_input(
    "Enter the Domain URL if used. It will override Base URL above. Example https://d-vegas.rossum.app/api:"
)

BASE_URL = DOMAIN_URL if DOMAIN_URL else CLUSTER_URL
client = rs.AsyncRequestClient(TOKEN, BASE_URL)

HOOK_TEMPLATE_ID = st.text_input("Hook Template ID:", "39")
BREAK_AFTER_SUCCESSFULL_RESULTS = st.checkbox("Break After Successful Results", True)
# IGNORE_CONDITIONS = st.checkbox("Ignore Conditions", True)
st.text(
    "Ignore Conditions is not supported yet. Query with conditions will be counted as valid and executed below."
)
CHECK_QUEUE_IDS_LIMITATIONS = st.checkbox("Check Queue IDs Limitations.", True)
STAGED_PIPELINE = st.checkbox("Staged Pipeline", False)
st.text("Staged Pipeline is not supported yet")
# STAGED_PIPELINE = False

TARGET_SCHEMA_ID = st.text_input("Target Schema ID:", "")
ANNOTATION_LIST = st.text_area("Annotation ID:", "").split(",")
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
        pipeline_result = {}
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
                pipeline = mvf.prepare_pipeline(query)

                tabs = []
                tab_names = []

                for i, stage in enumerate(pipeline):
                    pipeline_result = await client.data_storage_aggregate(
                        collectionName=dataset, pipeline=stage
                    )
                    tabs.append(pipeline_result)
                    tab_names.append(f"Stage {i+1}")

                    # mvf.visualize_result(stage[-1], pipeline_result, signature + str(i))
                st.write(
                    "More than one stage is found. Preparing data for pipeline view.."
                )
                tab = st.tabs(tab_names)
                for i, stage in enumerate(pipeline):
                    with tab[i]:
                        mvf.visualize_result(
                            stage[-1],
                            tabs[i],
                            signature + str(i) + " " + "Pipeline",
                            col2_expanded=False,
                        )

            else:
                result = await client.data_storage_aggregate(
                    collectionName=dataset, pipeline=query["aggregate"]
                )
                mvf.visualize_result(query, result, signature)

        else:
            st.write("No Find or Aggregate has been found or there is an empty query")

        if (
            result.get("result") or pipeline_result.get("result")
        ) and BREAK_AFTER_SUCCESSFULL_RESULTS:
            st.write("The result above will be shown in the UI!")
            break


def run_async(func):
    return asyncio.run(func)


if st.button("Check Annotation"):
    run_async(main())
