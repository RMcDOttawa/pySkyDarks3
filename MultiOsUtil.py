# Utilities to help program run on multiple OS - for now, windows and mac
# Helps locate resource files, end-running around the problems I've been having
# with the various native bundle packaging utilities that I can't get working
import os

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QLabel, QCheckBox, QRadioButton, QLineEdit, QPushButton, QDateEdit, QTimeEdit


class MultiOsUtil:

    LAST_ADDFRAME_SIZE_SETTING = "last_addframe_dialog_size"
    LAST_BULKADD_SIZE_SETTING = "last_bulkadd_dialog_size"
    LAST_WINDOW_SIZE_SETTING = "last_window_size"
    STANDARD_FONT_SIZE_SETTING = "standard_font_size"
    STANDARD_FONT_SIZE = 12
    MAIN_TITLE_LABEL_PREFIX = "MainTitle_"
    MAIN_TITLE_FONT_SIZE_INCREMENT = 6
    SUBTITLE_LABEL_PREFIX = "Subtitle_"
    SUBTITLE_FONT_SIZE_INCREMENT = 3

    # Generate a file's full path, given the file name, and having the
    # file reside in the same directory where the running program resides

    @classmethod
    def path_for_file_in_program_directory(cls, file_name: str) -> str:
        """Determine full absolute path to a file located in the program directory"""
        program_full_path = os.path.realpath(__file__)
        directory_name = os.path.dirname(program_full_path)
        path_to_file = f"{directory_name}/{file_name}"
        return path_to_file

    # Set all the items in the given UI tree with settable font sizes to
    # the given font size.  Except labels.  Check if their name indicates they
    # are headings and, if so, set larger by given increment.

    @classmethod
    def set_font_sizes(cls, parent: QObject,
                       standard_size: int,
                       title_prefix: str,
                       title_increment: int,
                       subtitle_prefix: str,
                       subtitle_increment: int):
        """Set font sizes of all UI elements"""
        # print(f"set_font_sizes({parent},{standard_size},{title_prefix},"
        #       f"{title_increment},{subtitle_prefix},{subtitle_increment})")
        children = parent.children()
        for child in children:
            # We'll only change the font size of labels and controls,
            # not collections
            desired_font_size = standard_size
            set_size = False
            child_name = child.objectName()
            if isinstance(child, QLabel):
                # Set label to standard size or an increment depending on name
                set_size = True
                if child_name.startswith(title_prefix):
                    # print(f"Increment title label: {child_name}")
                    desired_font_size = standard_size + title_increment
                elif child_name.startswith(subtitle_prefix):
                    # print(f"Increment subtitle label: {child_name}")
                    desired_font_size = standard_size + subtitle_increment
                else:
                    pass
                    # print(f"Increment normal label: {child_name}")
            elif isinstance(child, QCheckBox) \
                    or isinstance(child, QRadioButton) \
                    or isinstance(child, QLineEdit) \
                    or isinstance(child, QPushButton) \
                    or isinstance(child, QDateEdit) \
                    or isinstance(child, QTimeEdit):
                set_size = True
                # print(f"Increment other fontable field: {child_name}")
            if set_size:
                child_font = child.font()
                child_font.setPointSize(desired_font_size)
                child.setFont(child_font)
            # Recursively handle the children of this item as subtrees of their own
            cls.set_font_sizes(child, standard_size, title_prefix, title_increment,
                               subtitle_prefix, subtitle_increment)
