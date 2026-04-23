"""Module for managing enterprise projects and document reports."""
import re

from datetime import datetime, timezone
from freezegun import freeze_time
from uc3m_consulting.enterprise_project import EnterpriseProject
from uc3m_consulting.enterprise_management_exception import EnterpriseManagementException
from uc3m_consulting.project_document import ProjectDocument
from uc3m_consulting.projects_json_store import ProjectsJsonStore
from uc3m_consulting.documents_json_store import DocumentsJsonStore
from uc3m_consulting.reports_json_store import ReportsJsonStore

class EnterpriseManager:
    """Class for providing the methods for managing the orders.

    Implements the Singleton pattern: only one instance of EnterpriseManager
    can exist. All calls to EnterpriseManager() return the same instance.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @staticmethod
    def _compute_cif_control_digit(middle_digits: str) -> int:
        """Computes the expected CIF control digit from the 7 middle digits."""
        odd_pos_sum = 0
        even_pos_sum = 0
        for i, digit_char in enumerate(middle_digits):
            if i % 2 == 0:
                doubled = int(digit_char) * 2
                if doubled > 9:
                    odd_pos_sum = odd_pos_sum + (doubled // 10) + (doubled % 10)
                else:
                    odd_pos_sum = odd_pos_sum + doubled
            else:
                even_pos_sum = even_pos_sum + int(digit_char)

        total = odd_pos_sum + even_pos_sum
        total_last_digit = total % 10
        expected_control = 10 - total_last_digit
        if expected_control == 10:
            expected_control = 0
        return expected_control

    @staticmethod
    def _validate_date_format(date_str: str):
        """Validates that a date string matches dd/mm/yyyy format and is parseable.

        Returns the parsed date object on success.
        Raises EnterpriseManagementException with 'Invalid date format' otherwise.
        """
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        if not date_pattern.fullmatch(date_str):
            raise EnterpriseManagementException("Invalid date format")
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise EnterpriseManagementException("Invalid date format") from ex

    @staticmethod
    def validate_cif(cif: str):
        """validates a cif number """
        if not isinstance(cif, str):
            raise EnterpriseManagementException("CIF code must be a string")
        cif_pattern = re.compile(r"^[ABCDEFGHJKNPQRSUVW]\d{7}[0-9A-J]$")
        if not cif_pattern.fullmatch(cif):
            raise EnterpriseManagementException("Invalid CIF format")

        letter = cif[0]
        middle_digits = cif[1:8]
        control_char = cif[8]

        expected_control = EnterpriseManager._compute_cif_control_digit(middle_digits)

        control_letter_map = "JABCDEFGHI"

        if letter in ('A', 'B', 'E', 'H'):
            if str(expected_control) != control_char:
                raise EnterpriseManagementException("Invalid CIF character control number")
        elif letter in ('P', 'Q', 'S', 'K'):
            if control_letter_map[expected_control] != control_char:
                raise EnterpriseManagementException("Invalid CIF character control letter")
        else:
            raise EnterpriseManagementException("CIF type not supported")
        return True

    def validate_starting_date(self, starting_date: str):
        """validates the  date format  using regex"""
        my_date = self._validate_date_format(starting_date)

        if my_date < datetime.now(timezone.utc).date():
            raise EnterpriseManagementException("Project's date must be today or later.")

        if my_date.year < 2025 or my_date.year > 2050:
            raise EnterpriseManagementException("Invalid date format")
        return starting_date

    @staticmethod
    def _validate_acronym(project_acronym: str):
        """Validates the project acronym format."""
        acronym_pattern = re.compile(r"^[a-zA-Z0-9]{5,10}")
        if not acronym_pattern.fullmatch(project_acronym):
            raise EnterpriseManagementException("Invalid acronym")

    @staticmethod
    def _validate_description(project_description: str):
        """Validates the project description format."""
        description_pattern = re.compile(r"^.{10,30}$")
        if not description_pattern.fullmatch(project_description):
            raise EnterpriseManagementException("Invalid description format")

    @staticmethod
    def _validate_department(department: str):
        """Validates the department name."""
        department_pattern = re.compile(r"(HR|FINANCE|LEGAL|LOGISTICS)")
        if not department_pattern.fullmatch(department):
            raise EnterpriseManagementException("Invalid department")

    @staticmethod
    def _validate_budget(budget):
        """Validates the budget value format and range."""
        try:
            budget_value = float(budget)
        except ValueError as exc:
            raise EnterpriseManagementException("Invalid budget amount") from exc

        budget_str = str(budget_value)
        if '.' in budget_str:
            decimal_places = len(budget_str.split('.')[1])
            if decimal_places > 2:
                raise EnterpriseManagementException("Invalid budget amount")

        if budget_value < 50000 or budget_value > 1000000:
            raise EnterpriseManagementException("Invalid budget amount")

    #pylint: disable=too-many-arguments, too-many-positional-arguments
    def register_project(self,
                         company_cif: str,
                         project_acronym: str,
                         project_description: str,
                         department: str,
                         date: str,
                         budget: str):
        """registers a new project"""
        self.validate_cif(company_cif)
        self._validate_acronym(project_acronym)
        self._validate_description(project_description)
        self._validate_department(department)
        self.validate_starting_date(date)
        self._validate_budget(budget)

        new_project = EnterpriseProject(company_cif=company_cif,
                                        project_acronym=project_acronym,
                                        project_description=project_description,
                                        department=department,
                                        starting_date=date,
                                        project_budget=budget)

        projects_store = ProjectsJsonStore()
        projects_store.add_project(new_project.to_json())
        return new_project.project_id

    @staticmethod
    def _count_documents_for_date(date_str: str) -> int:
        """Counts documents registered on the given date, verifying their signatures.

        Reads the documents store and, for each entry whose register_date falls
        on date_str, rebuilds the ProjectDocument (under a frozen clock matching
        the original timestamp) and compares signatures. Raises if any signature
        mismatches; returns the count of valid documents found.
        """
        documents_store = DocumentsJsonStore()
        documents_list = documents_store.load_documents()

        documents_found = 0
        for document_entry in documents_list:
            timestamp = document_entry["register_date"]
            document_date_str = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")
            if document_date_str != date_str:
                continue
            document_datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            with freeze_time(document_datetime):
                rebuilt_document = ProjectDocument(document_entry["project_id"],
                                                   document_entry["file_name"])
                if rebuilt_document.document_signature != document_entry["document_signature"]:
                    raise EnterpriseManagementException("Inconsistent document signature")
                documents_found = documents_found + 1
        return documents_found

    @staticmethod
    def _append_report_entry(date_str: str, documents_found: int):
        """Appends a new report entry to the reports store."""
        report_entry = {"Querydate":  date_str,
                        "ReportDate": datetime.now(timezone.utc).timestamp(),
                        "Numfiles": documents_found}
        reports_store = ReportsJsonStore()
        reports_store.append_report(report_entry)

    def generate_documents_report(self, date_str):
        """
        Generates a JSON report counting valid documents for a specific date.

        Validates the date, counts matching documents (checking cryptographic
        signatures for integrity), and appends a report entry to the store.

        Args:
            date_str (str): date to query, in dd/mm/yyyy format.

        Returns:
            int: number of documents found.

        Raises:
            EnterpriseManagementException: On invalid date, file IO errors,
                missing data, or cryptographic integrity failure.
        """
        self._validate_date_format(date_str)
        documents_found = self._count_documents_for_date(date_str)
        if documents_found == 0:
            raise EnterpriseManagementException("No documents found")
        self._append_report_entry(date_str, documents_found)
        return documents_found
