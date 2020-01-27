# -*- mode: python ; coding: utf-8 -*-

#  pyinstaller spec file for building a standalone windows application
#  build machine must have python and all needed packages installed, but the resulting
#  application is stand-alone and can run on any windows machine

block_cipher = None


a = Analysis(['pySkyDarks3.py'],
             pathex=['\\\\Mac\\Dropbox\\Dropbox\\EWHO\\Application Development\\pySkyDarks3'],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='pySkyDarks3',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
