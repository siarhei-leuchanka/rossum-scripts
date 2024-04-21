import pandas as pd
from IPython.display import display
from rs_classes import annotation as annotation


def form_dataset_for_text_value_analysis(
    obj: annotation.Annotation, key: str, field_id: str
) -> pd.DataFrame:
    temp_list = []
    datapoints = obj.find_by_schema_id(obj.content_data, field_id)
    if datapoints:
        for datapoint in datapoints:
            content_value = datapoint["content"]["value"]
            position_check = (
                "  || => Manual"
                if not datapoint["content"].get("position", False)
                and content_value != ""
                else ""
            )
            temp_list.append({"IDs": key, field_id: f"{content_value}{position_check}"})
        temp_df = pd.DataFrame(temp_list)
        temp_df.set_index("IDs", inplace=True)
        return temp_df
    # if no datapoints return empty df
    return pd.DataFrame()


def text_value_analysis(
    field_ids: list, annotations_collection: dict, base_url: str
) -> pd.DataFrame:
    output = pd.DataFrame()
    for key, obj in annotations_collection.items():
        temp_merged_df = pd.DataFrame([{"IDs": key, "Address": f"{base_url}/{key}"}])
        temp_merged_df.set_index("IDs", inplace=True)
        for field_id in field_ids:
            temp_merged_df = temp_merged_df.merge(
                form_dataset_for_text_value_analysis(obj, key, field_id),
                how="outer",
                left_index=True,
                right_index=True,
            )
        output = pd.concat([output, temp_merged_df])

    return output
