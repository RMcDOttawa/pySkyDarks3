from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QVariant, Qt, QSettings
from PyQt5.QtGui import QFont

from FrameSet import FrameSet
from MultiOsUtil import MultiOsUtil
from tracelog import *

class FrameSetSessionTableModel(QAbstractTableModel):
    _columnHeaders = ("Frames", "Type", "Seconds", "Binned", "Done")

    # Constructor takes and keeps a pointer to the data model
    def __init__(self, session_framesets_list):
        QAbstractTableModel.__init__(self)
        self._framesets_list = session_framesets_list

    # Methods required by the parent data model
    #tracelog
    def rowCount(self, parent_model_index) -> int:
        return len(self._framesets_list)

    #tracelog
    def columnCount(self, parent_model_index) -> int:
        return FrameSet.NUMBER_OF_DISPLAY_FIELDS

    #tracelog
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_num: int = index.row()
        column_num: int = index.column()
        # print(f"data(({row_num},{column_num}),{role})")
        if role == Qt.DisplayRole:
            assert ((row_num >= 0) & (row_num < len(self._framesets_list)))
            the_frame_set: FrameSet = self._framesets_list[row_num]
            result: QVariant = QVariant(the_frame_set.fieldNumberAsString(column_num))
        elif role == Qt.FontRole:
            settings = QSettings()
            standard_font_size = settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING)
            font = QFont()
            font.setPointSize(standard_font_size)
            result = font
        else:
            result = QVariant()
        return result

    #tracelog
    def headerData(self, column_number, orientation, role):
        # print(f"headerData({column_number}, {orientation}, {role}) STUB")
        result = QVariant()
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                assert ((column_number >= 0) & (column_number < len(self._columnHeaders)))
                result = self._columnHeaders[column_number]
            elif role == Qt.FontRole:
                settings = QSettings()
                standard_font_size = settings.value(MultiOsUtil.STANDARD_FONT_SIZE_SETTING)
                font = QFont()
                font.setPointSize(standard_font_size)
                font.setBold(True)
                result = font
        return result

    # Received notice that one of the stored frame sets has changed (at time of writing,
    # this would be a change to the number-completed field).  Emit the appropriate signals so
    # that the table view updates.
    #tracelog
    def table_row_changed(self, row_index: int):
        # print(f"FrameSetSessionTableModel/table_row_changed({row_index})")
        assert (0 <= row_index < len(self._framesets_list))
        top_left_index = self.index(row_index, 0)
        bottom_right_index = self.index(row_index, len(self._columnHeaders) - 1)
        roles = [Qt.DisplayRole] * len(self._columnHeaders)
        self.dataChanged.emit(top_left_index, bottom_right_index, roles)
