@REM
@REM {% include 'generated_by.txt' %}
@REM
@ECHO OFF

cd %~dp0
bash.exe -c "BUILD_TYPE=Debug ./build.sh %*"
