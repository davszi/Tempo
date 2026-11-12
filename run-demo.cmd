@echo off
setlocal
pushd "%~dp0" || exit /b 1

python -B -c "import fsrs" >nul 2>&1
if errorlevel 1 (
    for /d %%D in (".build\tempo-fsrs-verify-*") do (
        if exist "%%~fD\fsrs\__init__.py" set "PYTHONPATH=%%~fD"
    )
)
python -B -c "import fsrs" >nul 2>&1
if errorlevel 1 (
    echo Install the dependencies with: python -m pip install -r requirements.txt
    popd
    exit /b 1
)

python -B -m tempo.demo --database demo/tempo_demo.sqlite --weights demo/fitted_global.csv %*
set "TEMPO_DEMO_EXIT=%ERRORLEVEL%"
popd
exit /b %TEMPO_DEMO_EXIT%
