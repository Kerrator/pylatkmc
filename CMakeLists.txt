cmake_minimum_required(VERSION 3.20)
project(pylatkmc
    VERSION 0.1.0
    LANGUAGES C
    DESCRIPTION "Species-aware on-lattice KMC solver, driven by Python-generated C"
)

# --------------------------------------------------------------
# Build options
# --------------------------------------------------------------
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Which model to compile. Defaults to ni_fe_cr_v1; override with -DMODEL=<name>.
set(MODEL "ni_fe_cr_v1" CACHE STRING "Model name under models/ to compile")

# Codegen output is REQUIRED since M2. If you want to test that the runtime
# backbone at least parses without any generated files, set -DREQUIRE_GENERATED=OFF
# explicitly — but you will NOT get a working binary without codegen.
option(REQUIRE_GENERATED "Fail if models/<MODEL>/generated/ is empty" ON)

# --------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------
find_package(MPI REQUIRED COMPONENTS C)

# --------------------------------------------------------------
# Paths
# --------------------------------------------------------------
set(PYLATKMC_RUNTIME_DIR  "${CMAKE_SOURCE_DIR}/runtime/src")
set(PYLATKMC_MODEL_DIR    "${CMAKE_SOURCE_DIR}/models/${MODEL}")
set(PYLATKMC_GEN_DIR      "${PYLATKMC_MODEL_DIR}/generated")

if(NOT EXISTS "${PYLATKMC_MODEL_DIR}")
    message(FATAL_ERROR
        "Model dir not found: ${PYLATKMC_MODEL_DIR}\n"
        "Available models: see models/ subdir. Override with -DMODEL=<name>."
    )
endif()

# Peek at generated/. In M1 it may be empty (codegen not yet run).
file(GLOB PYLATKMC_GEN_C "${PYLATKMC_GEN_DIR}/*.c")
file(GLOB PYLATKMC_GEN_H "${PYLATKMC_GEN_DIR}/*.h")
list(LENGTH PYLATKMC_GEN_C _n_gen_c)
if(_n_gen_c EQUAL 0)
    if(REQUIRE_GENERATED)
        message(FATAL_ERROR
            "No generated/*.c found under ${PYLATKMC_GEN_DIR}.\n"
            "Run `pylatkmc-gen build ${PYLATKMC_MODEL_DIR}/${MODEL}.kmcspec.toml` first."
        )
    else()
        message(STATUS "pylatkmc: no codegen output for MODEL=${MODEL} — "
                       "falling back to runtime/src/core/ stubs (M1 scaffold mode).")
    endif()
endif()

# --------------------------------------------------------------
# Sources
# --------------------------------------------------------------
file(GLOB PYLATKMC_CORE_SRC CONFIGURE_DEPENDS "${PYLATKMC_RUNTIME_DIR}/core/*.c")
file(GLOB PYLATKMC_IO_SRC   CONFIGURE_DEPENDS "${PYLATKMC_RUNTIME_DIR}/io/*.c")
file(GLOB PYLATKMC_MPI_SRC  CONFIGURE_DEPENDS "${PYLATKMC_RUNTIME_DIR}/mpi/*.c")

# If codegen output exists, its .c files REPLACE the corresponding stub in
# runtime/src/core/ (events.h / ratetable.c / avail.c). We don't remove from
# PYLATKMC_CORE_SRC because the include-path ordering handles header shadowing;
# for .c replacement we preferentially compile the generated file AND drop
# the stub to avoid duplicate-symbol link errors.
if(_n_gen_c GREATER 0)
    foreach(_gen_c ${PYLATKMC_GEN_C})
        get_filename_component(_gen_name "${_gen_c}" NAME)
        set(_stub_c "${PYLATKMC_RUNTIME_DIR}/core/${_gen_name}")
        if(EXISTS "${_stub_c}")
            list(REMOVE_ITEM PYLATKMC_CORE_SRC "${_stub_c}")
            message(STATUS "pylatkmc: generated ${_gen_name} replaces runtime stub.")
        endif()
    endforeach()
endif()

# --------------------------------------------------------------
# Library: runtime backbone (+ generated per-model)
# --------------------------------------------------------------
add_library(pylatkmc_lib STATIC
    ${PYLATKMC_CORE_SRC}
    ${PYLATKMC_IO_SRC}
    ${PYLATKMC_MPI_SRC}
    ${PYLATKMC_GEN_C}
)

# Include-path order matters: generated/ must come first so generated headers
# shadow the scaffold stubs in runtime/src/core/.
target_include_directories(pylatkmc_lib PUBLIC
    ${PYLATKMC_GEN_DIR}
    ${PYLATKMC_RUNTIME_DIR}
    ${PYLATKMC_RUNTIME_DIR}/core
    ${PYLATKMC_RUNTIME_DIR}/io
    ${PYLATKMC_RUNTIME_DIR}/mpi
)

target_link_libraries(pylatkmc_lib PUBLIC MPI::MPI_C m)

target_compile_options(pylatkmc_lib PRIVATE
    -O3 -march=native -Wall -Wextra -Wpedantic
    $<$<CONFIG:Debug>:-O0 -g -fsanitize=address,undefined>
)
target_link_options(pylatkmc_lib PRIVATE
    $<$<CONFIG:Debug>:-fsanitize=address,undefined>
)

# --------------------------------------------------------------
# Executable
# --------------------------------------------------------------
add_executable(pylatkmc_${MODEL} "${PYLATKMC_RUNTIME_DIR}/main.c")
target_link_libraries(pylatkmc_${MODEL} PRIVATE pylatkmc_lib)

# --------------------------------------------------------------
# Tests (C unit tests)
# --------------------------------------------------------------
enable_testing()
if(EXISTS "${CMAKE_SOURCE_DIR}/tests/unit_c/CMakeLists.txt")
    add_subdirectory(tests/unit_c)
endif()

# --------------------------------------------------------------
# Install
# --------------------------------------------------------------
install(TARGETS pylatkmc_${MODEL} RUNTIME DESTINATION bin)

# --------------------------------------------------------------
# Status
# --------------------------------------------------------------
message(STATUS "pylatkmc build summary:")
message(STATUS "  MODEL            = ${MODEL}")
message(STATUS "  RUNTIME_DIR      = ${PYLATKMC_RUNTIME_DIR}")
message(STATUS "  MODEL_DIR        = ${PYLATKMC_MODEL_DIR}")
message(STATUS "  GEN_DIR          = ${PYLATKMC_GEN_DIR}")
message(STATUS "  generated .c     = ${_n_gen_c} file(s)")
message(STATUS "  CMAKE_BUILD_TYPE = ${CMAKE_BUILD_TYPE}")
