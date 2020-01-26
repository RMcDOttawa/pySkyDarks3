#!/bin/bash -x
rm pySkyDarks3.spec
rm -rf dist
rm -rf build
pyinstaller pySkyDarks3.py \
		    --onefile \
		    --windowed \
			--noconfirm \
			--add-data MainWindow.ui:. \
			--add-data AddFrameSet.ui:. \
			--add-data BulkEntry.ui:./
