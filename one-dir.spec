# -*- mode: python ; coding: utf-8 -*-

# This spec file is used with pyinstaller to generate a minimal unix executable that must
# be run from within the created directory, where all the file dependencies will be located

block_cipher = None


a = Analysis(['pySkyDarks3.py'],
             pathex=['/Users/richard/DropBox/dropbox/EWHO/Application Development/pySkyDarks3'],
             binaries=[],
             datas=[('MainWindow.ui', '.'),
             ('BulkEntry.ui', '.'),
             ('AddFrameSet.ui', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='pySkyDarks3',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='pySkyDarks3')
