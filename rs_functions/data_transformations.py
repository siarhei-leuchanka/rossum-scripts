import pandas as pd
from IPython.display import display
from rs_classes import annotation as annotation


def form_dataset_for_text_value_analysis(
    obj: annotation.Annotation, key: str, field_id: str
) -> pd.DataFrame:
    temp_list = []

    metadata = obj.metadata

    if field_id.split(".")[0] == "meta":
        temp_list.append(
            {"IDs": key, field_id: metadata.get(field_id.split(".")[1], None)}
        )
        temp_df = pd.DataFrame(temp_list)
        temp_df.set_index("IDs", inplace=True)
        return temp_df
    else:
        datapoints = find_by_schema_id(obj.annotation_content, field_id)
        if datapoints:
            for datapoint in datapoints:
                content_value = datapoint["content"]["value"]
                position_check = (
                    "  || => Manual"
                    if not datapoint["content"].get("position", False)
                    and content_value != ""
                    else ""
                )
                temp_list.append(
                    {"IDs": key, field_id: f"{content_value}{position_check}"}
                )
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


def find_by_schema_id(content, schema_id: str):
    """
    Return all datapoints matching a schema id.
    :param content: annotation content tree
    :param schema_id: f
    :return: the list of datapoints matching the schema ID
    """
    accumulator = []
    for node in content:
        if node["schema_id"] == schema_id:
            accumulator.append(node)
        elif "children" in node:
            accumulator.extend(find_by_schema_id(node["children"], schema_id))

    return accumulator


def get_positions(annotation, field_id):
    position_data = []
    field_id_data = find_by_schema_id(annotation.annotation_content, field_id)
    if field_id_data != []:
        for result in field_id_data:
            content = result["content"]
            position_data.append(
                {
                    "annotation_id": annotation.id,
                    "field_id": field_id,
                    "page": content.get("page", None),
                    "x1": content["position"][0]
                    if content.get("position", None)
                    else None,
                    "y1": content["position"][1]
                    if content.get("position", None)
                    else None,
                    "x2": content["position"][2]
                    if content.get("position", None)
                    else None,
                    "y2": content["position"][3]
                    if content.get("position", None)
                    else None,
                    "status": "exists",
                }
            )
    else:
        position_data.append(
            {
                "annotation_id": annotation.id,
                "field_id": field_id,
                "page": None,
                "x1": None,
                "y1": None,
                "x2": None,
                "y2": None,
                "status": "absent_in_schema",
            }
        )

    return position_data


def position_analysis(annotations_collection, field_id, slicer_field_id):
    output = pd.DataFrame()
    for obj in annotations_collection.values():
        df = pd.DataFrame()
        pages_df = pd.DataFrame(obj.page_data)
        positions = get_positions(obj, field_id)
        slicer = find_by_schema_id(
            obj.annotation_content, slicer_field_id
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
