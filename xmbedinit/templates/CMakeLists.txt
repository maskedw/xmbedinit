cmake_minimum_required(VERSION 2.8)
project({{ project_name }})
set(executable {{ project_name }})

enable_language(C CXX ASM)

set(cross                   arm-none-eabi-)
set(CMAKE_C_COMPILER        ccache)
set(CMAKE_CXX_COMPILER      ccache)
set(CMAKE_C_COMPILER_ARG1   ${cross}gcc)
set(CMAKE_CXX_COMPILER_ARG1 ${cross}g++)
set(CMAKE_STRIP             ${cross}strip)
set(CMAKE_SIZE              ${cross}size)
set(CMAKE_NM                ${cross}nm)
set(CMAKE_AR                ${cross}ar)
set(CMAKE_OBJCOPY           ${cross}objcopy)
set(CMAKE_OBJDUMP           ${cross}objdump)
set(CMAKE_RANLIB            ${cross}ranlib)

include_directories(
    .
)
include(CMake/mbed.cmake)

add_definitions(
    -D__STDC_CONSTANT_MACROS
)

# C++98
set(cxx_std_opt -std=gnu++98)

# C99
set(c_std_opt -std=gnu99)

set(arch_opts           ${mbed_arch_opts})
set(warning_opts        -Wno-sign-compare ${mbed_warning_opts})
set(c_extra_opts        ${mbed_c_extra_opts})
set(cxx_extra_opts      ${mbed_cxx_extra_opts})
set(comman_flags        -g3 ${arch_opts} ${warning_opts})
list(APPEND cflags      ${comman_flags} ${c_std_opt} ${c_extra_opts})
list(APPEND cxxflags    ${comman_flags} ${cxx_std_opt} ${cxx_extra_opts})

list(APPEND asmflags    ${mbed_asm_flags})
list(APPEND ldflags
    ${mbed_linker_flags}
    -T${CMAKE_CURRENT_SOURCE_DIR}/linker_script.ld
    -Wl,-Map=${executable}.map
    -specs=nosys.specs
    # Use newlib-nano
    -specs=nano.specs

    # Floating-Point Support for PRINTF and SCANF in GNU ARM Compile
    # http://japan.cypress.com/knowledge-base-article/floating-point-support-printf-and-scanf-gnu-arm-compiler-kba89724

    # -u _printf_float
)

string(REPLACE ";" " " cflags "${cflags}")
string(REPLACE ";" " " cxxflags "${cxxflags}")
string(REPLACE ";" " " asmflags "${asmflags}")
string(REPLACE ";" " " ldflags "${ldflags}")

set(CMAKE_C_FLAGS  ${cflags})
set(CMAKE_CXX_FLAGS ${cxxflags})
set(CMAKE_EXE_LINKER_FLAGS ${ldflags})
set(CMAKE_ASM_FLAGS ${asmflags} CACHE INTERNAL "asm compiler flags")
set(CMAKE_EXECUTABLE_SUFFIX ".elf")

add_executable( ${executable}
    main.cpp
    ${mbed_sources}
)

add_custom_command(TARGET ${executable} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${executable}>
            ${CMAKE_BINARY_DIR}/${executable}.bin
)

add_custom_command(TARGET ${executable} POST_BUILD
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${executable}>
)

target_link_libraries(${executable}
    ${mbed_link_libraries}
)
