"""
Cursor flow domain models.

Holds the data structure describing one discovered cursor execution flow.
This module contains no logic, only the plan definition.
"""

from dataclasses import dataclass


@dataclass
class CursorFlowPlan:
    cursor_name: str
    open_number: int
    fetch_number: int
    close_number: int
    open_paragraph: str
    fetch_paragraph: str
    close_paragraph: str
    eoc_condition: str
    business_paragraph: str
    open_index: int
    fetch_index: int
    business_index: int
    until_index: int