# PyInstaller 설정. 사용법은 README의 "exe로 만들기"를 보세요.
#   기본: 폴더 모양(dist/EMG-Dragon-Slayer/) - 켜질 때 빠르고 파일 바꾸기 쉽다
#   ONEFILE=1: exe 파일 하나로 묶는다 - 배포는 편하지만 켤 때마다 압축을 풀어서 느리다
#   EXE_CONSOLE=1: 검은 콘솔 창을 같이 띄운다 (--selftest 같은 점검용)
import os

from PyInstaller.utils.hooks import collect_submodules

NAME = "EMG-Dragon-Slayer"
onefile = os.environ.get("ONEFILE") == "1"
console = os.environ.get("EXE_CONSOLE") == "1"

a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=[("assets", "assets")],  # 그림, 글꼴, 소리, 음악
    hiddenimports=collect_submodules("serial"),  # 센서 포트 찾기(serial.tools.list_ports_*)는 운영체제마다 달라서 전부 넣는다
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)

if onefile:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=NAME, console=console, upx=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=console, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)
