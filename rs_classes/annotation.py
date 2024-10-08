# annotation.py


class Annotation:
    def __init__(self, annotation_metadata: dict) -> None:
        self._metadata = annotation_metadata
        self._page_data = []
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
    def page_data(self, page_meta):
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
