@echo off
setlocal
title Motor Insurance Analytics Dashboard
cd /d "%~dp0"

where streamlit >nul 2>nul
if not errorlevel 1 goto run_streamlit

where py >nul 2>nul
if errorlevel 1 goto missing_streamlit

py -m streamlit --version >nul 2>nul
if errorlevel 1 goto missing_streamlit

py -m streamlit run "%~dp0app\streamlit_app.py"
if errorlevel 1 (
    echo.
    echo The dashboard could not start. Review the error above.
    pause
    exit /b 1
)
goto done

:run_streamlit
streamlit run "%~dp0app\streamlit_app.py"
if errorlevel 1 (
    echo.
    echo The dashboard could not start. Review the error above.
    pause
    exit /b 1
)
goto done

:missing_streamlit
echo Streamlit was not found.
echo From this folder, install dependencies with: py -m pip install -r requirements.txt
pause
exit /b 1

:done
endlocal
