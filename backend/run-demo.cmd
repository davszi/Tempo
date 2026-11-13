@echo off
setlocal
pushd "%~dp0.." || exit /b 1

python -B -c "import fsrs" >nul 2>&1
if errorlevel 1 (
    echo Install the dependencies with: python -m pip install -r backend/requirements.txt
    popd
    exit /b 1
)

python -B -m backend.demo --database backend/tempo_demo.sqlite --weights backend/fitted_global.csv %*
set "TEMPO_DEMO_EXIT=%ERRORLEVEL%"
popd
exit /b %TEMPO_DEMO_EXIT%
