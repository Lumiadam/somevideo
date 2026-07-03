@echo off
chcp 65001 > nul
echo ===================================================
echo   正在啟動 享Video - 智慧影音推薦系統...
echo ===================================================
echo.

:: 檢查是否有 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python！請確認本機已安裝 Python 並將其加入系統 PATH 中。
    pause
    exit /b
)

:: 嘗試執行 streamlit
python -m streamlit run src/app.py
if %errorlevel% neq 0 (
    echo.
    echo [提示] 正在為您安裝必要的依賴套件，請稍候...
    pip install -r requirements.txt
    echo.
    echo [提示] 安裝完成，再次嘗試啟動系統...
    python -m streamlit run src/app.py
)

pause
