from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QVariant, Qt

from FrameSet import FrameSet
from tracelog import *


class FrameSetPlanTableModel (QAbstractTableModel):

    _columnHeaders = ("# Frames", "Type", "Exposure", "Binning", "Complete")

    # Constructor takes and keeps a pointer to the data model
    def __init__(self, the_data_model):
        QAbstractTableModel.__init__(self)
        self._dataModel = the_data_model

    # Methods required by the parent data model
    #tracelog
    def rowCount(self, parent_model_index: QModelIndex) -> int:
        # print(f"rowCount({parent_model_index}")
        return len(self._dataModel.get_saved_frame_sets())

    #tracelog
    def columnCount(self, parent_model_index) -> int:
        return FrameSet.NUMBER_OF_DISPLAY_FIELDS

    #tracelog
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_num: int = index.row()
        column_num: int = index.column()
        # print(f"data(({row_num},{column_num}),{role})")
        if role == Qt.DisplayRole:
            assert((row_num >= 0) & (row_num < len(self._dataModel.get_saved_frame_sets())))
            the_frame_set: FrameSet = self._dataModel.get_frame_set(row_num)
            result: QVariant = QVariant(the_frame_set.fieldNumberAsString(column_num))
        else:
            result = QVariant()
        return result

    #tracelog
    def headerData(self, column_number, orientation, role):
        # print(f"headerData({column_number}, {orientation}, {role})")
        result = QVariant()
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            assert((column_number >= 0) & (column_number < len(self._columnHeaders)))
            result = self._columnHeaders[column_number]
        return result

    # Add a frameset to the end of the list in this model
    @tracelog
    def addFrameSet(self, new_frame_set: FrameSet):
        frame_sets: [FrameSet] = self._dataModel.get_saved_frame_sets()
        self.beginInsertRows(QModelIndex(), len(frame_sets), len(frame_sets))
        self._dataModel.add_frame_set(new_frame_set)
        self.endInsertRows()

    # Insert a frameset into the list at the given index position
    @tracelog
    def insertFrameSet(self, new_frame_set: FrameSet, at_index: int):
        self.beginInsertRows(QModelIndex(), at_index, at_index)
        self._dataModel.insert_frame_set(new_frame_set, at_index)
        self.endInsertRows()

    # Delete the frameSet at the given index
    @tracelog
    def deleteRow(self, index_to_delete: int):
        num_frame_sets: int = len(self._dataModel.get_saved_frame_sets())
        assert ((index_to_delete >= 0) and (index_to_delete < num_frame_sets))
        self.beginRemoveRows(QModelIndex(), index_to_delete, index_to_delete)
        self._dataModel.delete_frame_set(index_to_delete)
        self.endRemoveRows()
