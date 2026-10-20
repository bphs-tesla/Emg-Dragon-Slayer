@echo off
REM Windows에서 더블클릭하거나 실행하면 dist\EMG-Dragon-Slayer\EMG-Dragon-Slayer.exe 가 만들어진다.
REM 사전 준비: uv 설치 (https://docs.astral.sh/uv/)
uv sync || goto :error
uv run pytest -q || goto :error
uv run pyinstaller --noconfirm --clean EMG-Dragon-Slayer.spec || goto :error
echo.
echo 완료: dist\EMG-Dragon-Slayer\EMG-Dragon-Slayer.exe
echo 이 폴더(EMG-Dragon-Slayer)를 통째로 옮기면 된다.
exit /b 0
:error
echo 실패했어요. 위 메시지를 확인하세요.
exit /b 1
