# PyInstaller spec for the itch.io build. Run `make package` (not this file directly).
# Produces one self-contained executable; config.json, assets/ and PLAYING.txt are
# copied next to it by the Makefile so players can edit them.

a = Analysis(["pac-man.py"], pathex=["."])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="pac-man", console=True, upx=False)
