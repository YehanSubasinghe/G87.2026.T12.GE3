"""Module containing the DocumentsJsonStore class for documents persistence."""
import json
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import TEST_DOCUMENTS_STORE_FILE


class DocumentsJsonStore:
    """Persistence layer for registered documents, backed by a JSON file."""

    def __init__(self):
        self._file_path = TEST_DOCUMENTS_STORE_FILE

    def load_documents(self):
        """Returns the list of stored documents.

        Raises EnterpriseManagementException if the file is missing or malformed.
        """
        try:
            with open(self._file_path, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file or file path") from ex
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex