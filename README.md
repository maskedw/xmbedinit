# xmbedinit

## Descriptions
This tool will help local development of mbed.

## Features
+ Copy the source of mbed's specified target only
+ CMake Build boilerplate to generate

## Supprted OS
+ Windows
+ `*nix`

## Requirement
+ Python2.7(Because mbed-cli only supports Python2)
+ Git
+ [mbed-cli](https://github.com/ARMmbed/mbed-cli)
+ [GNU Arm Embedded Toolchain](https://developer.arm.com/open-source/gnu-toolchain/gnu-rm/downloads)
+ [CMake](https://github.com/Kitware/CMake)
+ [ccache](https://github.com/ccache/ccache)
+ [Ninja](https://github.com/ninja-build/ninja)

## Installation
```sh
$ pip install git+https://github.com/maskedw/xmbedinit -U
```

## Usage

```sh
$ xmbedinit -h
usage: xmbedinit [-h] -m TARGET -T TAG [-d DEST] [-v]

This tool will help local development of mbed

optional arguments:
  -h, --help            show this help message and exit
  -m TARGET, --target TARGET
                        Compile target MCU. @see https://github.com/ARMmbed/mbed-cli (default: None)
  -T TAG, --tag TAG     Tag of mbed @see https://github.com/ARMmbed/mbed-os/releases (default: None)
  -d DEST, --dest DEST  Directory of export destination (default: .)
  -v, --verbose         Verbose output (default: False)
```

## Example
```sh
$ mkdir PROJECT-DIR
$ cd PROJECT-DIR
$ xmbedinit -m NUCLEO_L476RG -T mbed-os-5.7.2
$ ls -1
CMake/
CMakeLists.txt
build-compile_commands.sh
build-debug.bat
build-debug.sh
build-release.bat
build-release.sh
build.sh
linker_script.ld
main.cpp
mbed-os
xmbedinit.log
$ ./build-debug.sh
```
