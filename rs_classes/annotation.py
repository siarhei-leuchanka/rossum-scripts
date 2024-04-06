# annotation.py

import json


class Annotation:
    def __init__(self, metadata: json) -> None:
        self.metadata = metadata
        self.id = metadata.get("id", "na")
        self.queue = metadata.get("queue", "na").split("/")[-1]
        self.schema = metadata.get("schema", "na").split("/")[-1]

    def set_content(self, annotation: list) -> None:
        self.content_data = annotation

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
