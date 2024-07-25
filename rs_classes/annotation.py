# annotation.py

import json


class Annotation:
    def __init__(self, metadata: json) -> None:
        self.metadata = metadata
        self.id = metadata.get("id", "na")
        self.queue = metadata.get("queue", "na").split("/")[-1]
        self.schema = metadata.get("schema", "na").split("/")[-1]
        self._page_data = []

    def set_content(self, annotation: list) -> None:
        self.content_data = annotation
    
    def set_meta(self, annotation: list) -> None:
        self.meta = annotation

    def find_by_schema_id(self, content, schema_id: str):
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
                accumulator.extend(self.find_by_schema_id(node["children"], schema_id))

        return accumulator

    @property
    def page_data(self):
        return self._page_data

    @page_data.setter
    def set_page_data(self, page_meta):
        self.page_meta = page_meta
        for result in page_meta:
            self._page_data.append(
                {
                    "annotation_id": self.id,
                    "page_id": result["id"],
                    "page": result["number"],
                    "page_width": result["width"],
                    "page_height": result["height"],
                }
            )

    def get_positions(self, field_id):
        position_data = []
        field_id_data = self.find_by_schema_id(self.content_data, field_id)
        if field_id_data != []:
            for result in field_id_data:
                content = result["content"]
                position_data.append(
                    {
                        "annotation_id": self.id,
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
                    "annotation_id": self.id,
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
