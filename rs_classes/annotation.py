# annotation.py


class Annotation:
    def __init__(self, annotation_metadata: dict) -> None:
        self._metadata = annotation_metadata
        # self.id = metadata.get("id", "na")
        # self.queue = metadata.get("queue", "na").split("/")[-1]
        # self.schema = metadata.get("schema", "na").split("/")[-1]
        self._page_data = []
        # self.related_email_ids = []
        self._related_emails = []
        self._annotation_data = None

    @property
    def id(self):
        return self.metadata.get("id", "na")

    @property
    def metadata(self):
        return self._metadata

    @property
    def queue(self):
        return self.metadata.get("queue", "na").split("/")[-1]

    @property
    def schema(self):
        return self.metadata.get("schema", "na").split("/")[-1]

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

    @property
    def related_email_ids(self):
        if self.metadata:
            return [
                email.split("/")[-1] if email else None
                for email in self.metadata.get("related_emails", [])
            ]
        else:
            return None

    @property
    def related_emails(self):
        return self._related_emails

    @related_emails.setter
    def related_emails(self, email):
        self._related_emails.append(email)
        return self._related_emails

    @property
    def annotation_content(self):
        return self._annotation_data

    @annotation_content.setter
    def annotation_content(self, annotation):
        self._annotation_data = annotation

    # def set_meta(self, annotation: list) -> None:
    #     self.meta = annotation

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

    def get_positions(self, field_id):
        position_data = []
        field_id_data = self.find_by_schema_id(self.annotation_content, field_id)
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
