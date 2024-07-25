import pandas as pd
from IPython.display import display
from rs_classes import annotation as annotation


def form_dataset_for_text_value_analysis(
    obj: annotation.Annotation, key: str, field_id: str
) -> pd.DataFrame:
    temp_list = []
    if field_id.split(".")[0] == "meta":
        temp_list.append(
            {
                "IDs": key, 
                field_id: obj.meta.get(field_id.split(".")[1], None)
            }
        )
        temp_df = pd.DataFrame(temp_list)
        temp_df.set_index("IDs", inplace=True)
        return temp_df
    else:        
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


def position_analysis(annotations_collection, field_id, slicer_field_id):
    output = pd.DataFrame()
    for key, obj in annotations_collection.items():
        df = pd.DataFrame()
        pages_df = pd.DataFrame(obj.page_data)
        positions = obj.get_positions(field_id)
        slicer = obj.find_by_schema_id(
            obj.content_data, slicer_field_id
        )  ##ugly hot fix for header only fields
        if slicer:
            slicer = slicer[0]
            slicer_value = slicer.get("content", [])["value"]
        else:
            slicer_value = "EMPTY SLICER"
        if positions[0].get("page", False):  # hot fix for header only fields
            positions_df = pd.DataFrame(positions)
            df = pd.merge(
                positions_df[["annotation_id", "page", "x1", "y1", "x2", "y2"]],
                pages_df[["page", "page_width", "page_height"]],
                on="page",
                how="left",
            )

        df["slicer"] = slicer_value
        output = pd.concat([output, df])

    # Convert coordinates to percentages
    # Calculate center of bounding box
    output["center_x"] = (output["x1"] + output["x2"]) / 2
    output["center_y"] = (output["y1"] + output["y2"]) / 2

    # Convert coordinates to relative percentages
    output["center_x_percent"] = output["center_x"] / output["page_width"] * 100
    output["center_y_percent"] = output["center_y"] / output["page_height"] * 100

    return output
