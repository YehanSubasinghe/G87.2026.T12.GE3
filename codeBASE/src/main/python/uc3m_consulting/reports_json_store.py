"""Module containing the ReportsJsonStore class for documents-report persistence."""
import json
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import TEST_NUMDOCS_STORE_FILE


class ReportsJsonStore:
    """Persistence layer for documents-count reports, backed by a JSON file."""

    def __init__(self):
        self._file_path = TEST_NUMDOCS_STORE_FILE

    def load_reports(self):
        """Returns the list of stored reports, or an empty list if the file does not exist."""
        try:
            with open(self._file_path, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

    def save_reports(self, reports_list):
        """Writes the given reports list to the JSON file."""
        try:
            with open(self._file_path, "w", encoding="utf-8", newline="") as file:
                json.dump(reports_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file or file path") from ex

    def append_report(self, report_entry):
        """Appends a single report entry to the store."""
        reports_list = self.load_reports()
        reports_list.append(report_entry)
        self.save_reports(reports_list)
