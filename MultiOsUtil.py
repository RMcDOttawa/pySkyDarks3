# Utilities to help program run on multiple OS - for now, windows and mac
# Helps locate resource files, end-running around the problems I've been having
# with the various native bundle packaging utilities that I can't get working
import os

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel

from tracelog import tracelog


class MultiOsUtil:

    # Generate a file's full path, given the file name, and having the
    # file reside in the same directory where the running program resides

    @classmethod
    def path_for_file_in_program_directory (cls, file_name: str) -> str:
        program_full_path = os.path.realpath(__file__)
        directory_name = os.path.dirname(program_full_path)
        path_to_file = f"{directory_name}/{file_name}"
        return path_to_file

    # Scan (recursively) all the elements in the UI and set the font for
    @classmethod
    def set_label_title_fonts(cls, parent: QObject, field_prefix: str, font: QFont):
        top_level_elements = parent.children()
        cls.traverse_and_set_label_fonts(top_level_elements, field_prefix, font)

    @classmethod
    def traverse_and_set_label_fonts(cls, element_list: [QObject],
                                     field_prefix: str, font: QFont):
        # Traverse the given list of top-level elements
        for element in element_list:
            if isinstance(element, QLabel):
                label_name = element.objectName()
                if label_name.startswith(field_prefix):
                    element.setFont(font)
            else:
                # In case this element has children, do a recursive traversal of them
                children = element.children()
                if children is not None:
                    cls.traverse_and_set_label_fonts(children, field_prefix, font)
