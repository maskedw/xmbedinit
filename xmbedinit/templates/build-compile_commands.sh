#!/bin/bash -e
##################################################
# {% include 'generated_by.txt' %}
##################################################
thisdir="$(dirname "${BASH_SOURCE:-$0}")"
thisdir="$(realpath "$thisdir")"
buildtype=$BUILD_TYPE

if [ -n "$BUILD_TYPE" ]; then
    buildtype=$BUILD_TYPE
else
    buildtype=Debug
fi

cd "$thisdir"
builddir=".compile_commands-${buildtype}"
if [ ! -d "$builddir" ]; then
    mkdir -p "$builddir"
fi

cd "$builddir"
cmake "${thisdir}" \
    -DCMAKE_TOOLCHAIN_FILE=CMake/toolchain-arm-none-eabi-gcc.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=1 \
    -DCMAKE_BUILD_TYPE="${buildtype}" \
    -G "Ninja" && cp compile_commands.json "$thisdir"
