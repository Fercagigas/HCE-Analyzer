@echo off
echo ========================================
echo Configurando entorno Conda HCE
echo ========================================
echo.

REM Verificar si conda está instalado
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda no está instalado o no está en el PATH
    echo Por favor instala Anaconda o Miniconda primero
    pause
    exit /b 1
)

echo [1/4] Creando entorno conda HCE...
conda env create -f environment.yml

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Falló la creación del entorno
    echo Intenta eliminar el entorno existente con: conda env remove -n HCE
    pause
    exit /b 1
)

echo.
echo [2/4] Activando entorno HCE...
call conda activate HCE

echo.
echo [3/4] Verificando instalación...
python --version
pip --version

echo.
echo [4/4] Instalación completada exitosamente!
echo.
echo ========================================
echo Para activar el entorno en el futuro:
echo   conda activate HCE
echo.
echo Para desactivar el entorno:
echo   conda deactivate
echo ========================================
echo.

pause
