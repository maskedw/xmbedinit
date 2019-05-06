# {% include 'generated_by.txt' %}

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_definitions(
        -DMBED_DEBUG
        -DDMBED_TRAP_ERRORS_ENABLED=1
    )
endif()

set(mbed_warning_opts
{%- for x in warning_opts %}
    {{ x }}
{%- endfor %}
)

set(mbed_arch_opts
{%- for x in arch_opts %}
    {{ x }}
{%- endfor %}
)

set(mbed_cxx_extra_opts
{%- for x in cxx_extra_opts %}
    {{ x }}
{%- endfor %}
)

set(mbed_c_extra_opts
{%- for x in c_extra_opts %}
    {{ x }}
{%- endfor %}
)
set(mbed_asm_flags
    -x
    assembler-with-cpp
    ${mbed_arch_opts}
    ${mbed_warning_opts}
    ${mbed_c_extra_opts}
)

set(mbed_link_libraries
{%- for x in link_libraries %}
    {{ x }}
{%- endfor %}
)

set(mbed_linker_flags
{%- for x in linker_flags %}
    {{ x }}
{%- endfor %}
)

set(mbed_config_definitions
{%- for x in config_definitions %}
    {{ x }}
{%- endfor %}
{%- for x in removed_config_definitions %}
    # lib:{{ x.removed_by }} {{ x.value }}
{%- endfor %}
)

include_directories(
{%- for x in include_dirs %}
    {{ x }}
{%- endfor %}
{%- for x in removed_include_dirs%}
    # lib:{{ x.removed_by }} {{ x.value }}
{%- endfor %}
)

add_definitions(
    ${mbed_config_definitions}
{%- for x in definitions %}
    {{ x }}
{%- endfor %}
)

set(mbed_sources
{%- for x in sources %}
    {{ x }}
{%- endfor %}
{%- for x in removed_sources %}
    # lib:{{ x.removed_by }} {{ x.value }}
{%- endfor %}
)
