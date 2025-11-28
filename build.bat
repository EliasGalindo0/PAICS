@echo off
echo ========================================
echo  PAICS - Build do Executavel
echo ========================================
echo.

echo [1/4] Instalando dependencias de build...
pip install pyinstaller

echo.
echo [2/4] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/4] Criando executavel...
pyinstaller paics.spec

echo.
echo [4/4] Verificando resultado...
if exist "dist\PAICS.exe" (
    echo.
    echo ========================================
    echo  BUILD CONCLUIDO COM SUCESSO!
    echo ========================================
    echo.
    echo O executavel esta em: dist\PAICS.exe
    echo.
    echo Para distribuir, envie a pasta 'dist' completa
    echo.
) else (
    echo.
    echo ========================================
    echo  ERRO NO BUILD!
    echo ========================================
    echo.
)

pause