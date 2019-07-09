# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['main.py'],
             binaries=[],
             datas=[('img', 'img\\'), ('translations', 'translations\\')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[
                 'lib2to3',
                 'scipy',
                 'pyserial',
                 'serial',
                 'Cython',
                 'matplotlib.WebAgg',
                 'matplotlib.Qt4Agg',
                 'PyQt4',
             ],
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
          name='fs_viewer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=False,
          icon='img\\sweep.ico')
