"""Module containing the ProjectsJsonStore class for projects persistence."""
import json
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.enterprise_manager_config import PROJECTS_STORE_FILE


class ProjectsJsonStore:
    """Persistence layer for enterprise projects, backed by a JSON file."""

    def __init__(self):
        self._file_path = PROJECTS_STORE_FILE

    def load_projects(self):
        """Returns the list of stored projects, or an empty list if the file does not exist."""
        try:
            with open(self._file_path, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as ex:
            raise EnterpriseManagementException("JSON Decode Error - Wrong JSON Format") from ex

    def save_projects(self, projects_list):
        """Writes the given projects list to the JSON file."""
        try:
            with open(self._file_path, "w", encoding="utf-8", newline="") as file:
                json.dump(projects_list, file, indent=2)
        except FileNotFoundError as ex:
            raise EnterpriseManagementException("Wrong file or file path") from ex

    def add_project(self, new_project_dict):
        """Adds a new project dict to the store after checking for duplicates.

        Raises EnterpriseManagementException if an identical project already exists.
        """
        projects_list = self.load_projects()
        for existing_project in projects_list:
            if existing_project == new_project_dict:
                raise EnterpriseManagementException("Duplicated project in projects list")
        projects_list.append(new_project_dict)
        self.save_projects(projects_list)
