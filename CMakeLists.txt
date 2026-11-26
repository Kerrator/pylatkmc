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

# Incremental active-set rebuild. OFF Release builds are sha256-identical to a
# build without the option, so everything it needs is inside if(PYLATKMC_INCREMENTAL).
option(PYLATKMC_INCREMENTAL "Compile the incremental active-set rebuild" OFF)
option(PYLATKMC_INCREMENTAL_ORACLE "Debug: check each incremental step against a full rebuild" OFF)
option(PYLATKMC_REPLAY_ORDER "Select incremental events in full-rebuild site order" OFF)
if(PYLATKMC_REPLAY_ORDER AND NOT PYLATKMC_INCREMENTAL)
    message(FATAL_ERROR "PYLATKMC_REPLAY_ORDER needs -DPYLATKMC_INCREMENTAL=ON")
endif()
if(PYLATKMC_INCREMENTAL_ORACLE AND NOT PYLATKMC_INCREMENTAL)
    message(FATAL_ERROR "PYLATKMC_INCREMENTAL_ORACLE needs -DPYLATKMC_INCREMENTAL=ON")
endif()

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
# Incremental builds only (PYLATKMC_INCREMENTAL=ON)
# --------------------------------------------------------------
if(PYLATKMC_INCREMENTAL)
    if(CMAKE_BINARY_DIR MATCHES "#")
        message(FATAL_ERROR "PYLATKMC_INCREMENTAL cannot use a build path containing '#': "
            "the derived header paths are passed as compile definitions.")
    endif()

    set(PYLATKMC_BUILD_HASH "" CACHE STRING
        "Build hash recorded by incremental builds; empty = git HEAD, -dirty if unclean")
    set(PYLATKMC_ORACLE_EVERY 1 CACHE STRING
        "Oracle builds check every N-th step (a build value, not an INI key)")
    string(LENGTH "${PYLATKMC_ORACLE_EVERY}" _inc_every_digits)
    if(NOT PYLATKMC_ORACLE_EVERY MATCHES "^[1-9][0-9]*$" OR _inc_every_digits GREATER 9)
        message(FATAL_ERROR "PYLATKMC_ORACLE_EVERY must be a positive integer of at most "
            "9 digits, not '${PYLATKMC_ORACLE_EVERY}'")
    endif()

    # The tool reads proclist.c, so nothing else in generated/ may be compiled:
    # with a second .c the linker can take that file's touchup_a.
    set(_inc_proclist "${PYLATKMC_GEN_DIR}/proclist.c")
    file(GLOB _inc_gen_names RELATIVE "${PYLATKMC_GEN_DIR}" "${PYLATKMC_GEN_DIR}/*.c")
    if(NOT _inc_gen_names STREQUAL "proclist.c")
        list(REMOVE_ITEM _inc_gen_names "proclist.c")
        string(REPLACE ";" ", " _inc_gen_extras "${_inc_gen_names}")
        message(FATAL_ERROR "PYLATKMC_INCREMENTAL needs exactly one generated source, proclist.c. "
            "In ${PYLATKMC_GEN_DIR}, remove: [${_inc_gen_extras}]")
    endif()

    set(_inc_dir "${CMAKE_BINARY_DIR}/incremental")
    set(_inc_script "${_inc_dir}/provenance.cmake")
    set(_inc_info_h "${_inc_dir}/pylatkmc_build_info.h")
    set(_inc_reach_h "${_inc_dir}/pt_reach_template.h")
    set(_inc_inputs "${_inc_dir}/build-inputs.txt")
    set(_inc_config "${_inc_dir}/build-config.txt")

    # Both derived headers are included by absolute path (below), so a stray
    # copy cannot be compiled. A stray is still a mistake: say so.
    foreach(_inc_where "${PYLATKMC_GEN_DIR}" "${PYLATKMC_RUNTIME_DIR}"
            "${PYLATKMC_RUNTIME_DIR}/core" "${PYLATKMC_RUNTIME_DIR}/io"
            "${PYLATKMC_RUNTIME_DIR}/mpi")
        foreach(_inc_name pt_reach_template.h pylatkmc_build_info.h)
            if(EXISTS "${_inc_where}/${_inc_name}")
                message(FATAL_ERROR "PYLATKMC_INCREMENTAL: remove the stray ${_inc_name}:\n"
                    "  ${_inc_where}/${_inc_name}\n"
                    "This header is derived in the build directory.")
            endif()
        endforeach()
    endforeach()

    find_package(Git QUIET)
    find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
    set(_inc_reach_tool "${CMAKE_SOURCE_DIR}/tools/gen_reach_template.py")

    # What the manifest records about the configuration, kept verbatim in a
    # file. Its sha is in the build-info header, so any change here relinks.
    string(TOUPPER "${CMAKE_BUILD_TYPE}" _inc_type)
    get_target_property(_inc_options pylatkmc_lib COMPILE_OPTIONS)
    list(JOIN _inc_options " " _inc_options)
    file(WRITE "${_inc_config}"
"model: ${MODEL}
PYLATKMC_INCREMENTAL: ${PYLATKMC_INCREMENTAL}
PYLATKMC_REPLAY_ORDER: ${PYLATKMC_REPLAY_ORDER}
PYLATKMC_INCREMENTAL_ORACLE: ${PYLATKMC_INCREMENTAL_ORACLE}
PYLATKMC_ORACLE_EVERY: ${PYLATKMC_ORACLE_EVERY}
REQUIRE_GENERATED: ${REQUIRE_GENERATED}
CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}
CMAKE_C_COMPILER: ${CMAKE_C_COMPILER}
CMAKE_C_COMPILER_ID: ${CMAKE_C_COMPILER_ID}
CMAKE_C_COMPILER_VERSION: ${CMAKE_C_COMPILER_VERSION}
pylatkmc_lib COMPILE_OPTIONS: ${_inc_options}
MPI_C_COMPILER: ${MPI_C_COMPILER}
MPI_C_COMPILE_OPTIONS: ${MPI_C_COMPILE_OPTIONS}
CMAKE_INTERPROCEDURAL_OPTIMIZATION: ${CMAKE_INTERPROCEDURAL_OPTIMIZATION}
CMAKE_C_FLAGS: ${CMAKE_C_FLAGS}
CMAKE_C_FLAGS_${_inc_type}: ${CMAKE_C_FLAGS_${_inc_type}}
CMAKE_EXE_LINKER_FLAGS: ${CMAKE_EXE_LINKER_FLAGS}
CMAKE_EXE_LINKER_FLAGS_${_inc_type}: ${CMAKE_EXE_LINKER_FLAGS_${_inc_type}}
")

    file(SHA256 "${_inc_config}" _inc_config_sha256)

    # One script, three modes. `hash` and `reach` run at configure (so a build
    # with no hash, or a proclist the tool cannot model, fails there) and again
    # at every build (so neither a commit, an edit, nor a file copied with an
    # old mtime can leave a stale hash or template). `manifest` runs after each
    # link.
    file(CONFIGURE OUTPUT "${_inc_script}" @ONLY CONTENT [=[
cmake_minimum_required(VERSION 3.20)
set(info_h "@_inc_info_h@")
set(reach_h "@_inc_reach_h@")
set(inputs_file "@_inc_inputs@")
set(config_file "@_inc_config@")
string(ASCII 34 q)
string(ASCII 10 nl)
if(MODE STREQUAL "hash")
    set(hash "@PYLATKMC_BUILD_HASH@")
    set(git "@GIT_EXECUTABLE@")
    set(src "@CMAKE_SOURCE_DIR@")
    if(hash STREQUAL "" AND git)
        # Tracked check: an export inside some other checkout must not take that HEAD.
        execute_process(COMMAND "${git}" -C "${src}" ls-files --error-unmatch CMakeLists.txt
            RESULT_VARIABLE ls_rc OUTPUT_QUIET ERROR_QUIET)
        if(ls_rc EQUAL 0)
            execute_process(COMMAND "${git}" -C "${src}" rev-parse HEAD
                RESULT_VARIABLE head_rc OUTPUT_VARIABLE head OUTPUT_STRIP_TRAILING_WHITESPACE)
            execute_process(COMMAND "${git}" --no-optional-locks -C "${src}" status
                        --porcelain --untracked-files=normal
                RESULT_VARIABLE status_rc OUTPUT_VARIABLE changes)
            if(head_rc EQUAL 0 AND status_rc EQUAL 0)
                set(hash "${head}")
                if(NOT changes STREQUAL "")
                    string(APPEND hash "-dirty")
                endif()
            endif()
        endif()
    endif()
    if(NOT hash MATCHES "^[0-9A-Za-z._+-]+$")
        message(FATAL_ERROR "PYLATKMC_INCREMENTAL needs a build hash: build from a git checkout "
            "or set -DPYLATKMC_BUILD_HASH=<hash> (letters, digits and . _ + - only).")
    endif()
    file(SHA256 "${config_file}" config_sha256)
    string(CONCAT header "#define PYLATKMC_BUILD_HASH ${q}${hash}${q}${nl}"
        "#define PYLATKMC_BUILD_CONFIG ${q}${config_sha256}${q}${nl}")
    if(EXISTS "${info_h}")
        file(READ "${info_h}" previous)
        if(NOT header STREQUAL previous)
            # GNU make 3.81 needs this header to outdate the outputs in whole seconds.
            execute_process(COMMAND "${CMAKE_COMMAND}" -E sleep 1)
        endif()
    endif()
    file(WRITE "${info_h}.tmp" "${header}")
    configure_file("${info_h}.tmp" "${info_h}" COPYONLY)
elseif(MODE STREQUAL "reach")
    file(SHA256 "${config_file}" config_sha256)
    if(DEFINED CONFIG AND NOT CONFIG STREQUAL config_sha256)
        message(FATAL_ERROR "the last configure did not finish: configure again")
    endif()
    set(generated "@PYLATKMC_GEN_DIR@")
    # Hash first: if proclist changes while the tool runs, the next build sees it.
    file(SHA256 "${generated}/proclist.c" c_sha256)
    file(SHA256 "${generated}/proclist.h" h_sha256)
    execute_process(COMMAND "@Python3_EXECUTABLE@" -I "@_inc_reach_tool@"
            "${generated}/proclist.c" "${reach_h}"
        RESULT_VARIABLE rc)
    if(NOT rc EQUAL 0)
        message(FATAL_ERROR "MODEL=@MODEL@ cannot be built with PYLATKMC_INCREMENTAL (see above).")
    endif()
    file(SHA256 "${reach_h}" reach_sha256)
    set(inputs "proclist_c_sha256: ${c_sha256}${nl}proclist_h_sha256: ${h_sha256}${nl}")
    string(APPEND inputs "reach_template_sha256: ${reach_sha256}${nl}")
    set(previous "")
    if(EXISTS "${inputs_file}")
        file(READ "${inputs_file}" previous)
    endif()
    if(NOT inputs STREQUAL previous)
        # Every object depends on this stamp. GNU make 3.81 compares whole seconds.
        # Future-dated objects (clock rollback or disk clock skew) can still be
        # stale after this pause. A fresh build directory avoids that case.
        if(NOT previous STREQUAL "")
            execute_process(COMMAND "${CMAKE_COMMAND}" -E sleep 1)
        endif()
        file(WRITE "${inputs_file}" "${inputs}")
    endif()
elseif(MODE STREQUAL "manifest")
    file(STRINGS "${info_h}" line REGEX "PYLATKMC_BUILD_HASH")
    string(REGEX MATCH "${q}(.*)${q}" quoted "${line}")
    set(hash "${CMAKE_MATCH_1}")
    file(READ "${config_file}" config)
    file(READ "${inputs_file}" inputs)
    file(SHA256 "${BINARY}" binary_sha256)
    file(WRITE "@CMAKE_BINARY_DIR@/BUILD-MANIFEST.txt"
"commit: ${hash}
${config}${inputs}binary_sha256: ${binary_sha256}
")
endif()
]=])

    execute_process(COMMAND "${CMAKE_COMMAND}" -DMODE=hash -P "${_inc_script}"
        RESULT_VARIABLE _inc_rc)
    if(NOT _inc_rc EQUAL 0)
        message(FATAL_ERROR "pylatkmc: no PYLATKMC_BUILD_HASH (see above).")
    endif()

    # Reach template: what touchup_a reads, derived from the model's proclist.
    # A proclist the tool cannot model (nn2 shells included) fails, naming the line.
    execute_process(COMMAND "${CMAKE_COMMAND}" -DMODE=reach -P "${_inc_script}"
        RESULT_VARIABLE _inc_rc)
    if(NOT _inc_rc EQUAL 0)
        message(FATAL_ERROR
            "pylatkmc: MODEL=${MODEL} cannot be built with PYLATKMC_INCREMENTAL (see above).")
    endif()

    add_custom_target(pylatkmc_build_info
        COMMAND "${CMAKE_COMMAND}" -DMODE=hash -P "${_inc_script}"
        COMMAND "${CMAKE_COMMAND}" -DMODE=reach "-DCONFIG=${_inc_config_sha256}" -P "${_inc_script}"
        BYPRODUCTS "${_inc_info_h}" "${_inc_reach_h}" "${_inc_inputs}"
        VERBATIM)
    add_dependencies(pylatkmc_lib pylatkmc_build_info)
    # proclist.h reaches several sources, so all of them follow the stamp.
    set_property(SOURCE ${PYLATKMC_CORE_SRC} ${PYLATKMC_IO_SRC} ${PYLATKMC_MPI_SRC}
            "${_inc_proclist}" "${PYLATKMC_RUNTIME_DIR}/main.c"
        APPEND PROPERTY OBJECT_DEPENDS "${_inc_inputs}")

    # CMake's include scanner cannot follow these macro-based includes.
    set_property(SOURCE "${PYLATKMC_RUNTIME_DIR}/mpi/replica.c"
        APPEND PROPERTY OBJECT_DEPENDS "${_inc_info_h}")
    set_property(SOURCE "${PYLATKMC_RUNTIME_DIR}/core/incremental.c"
        APPEND PROPERTY OBJECT_DEPENDS "${_inc_reach_h}")

    # PUBLIC: the definition changes struct State, so main.c must see it too.
    target_compile_definitions(pylatkmc_lib PUBLIC PYLATKMC_INCREMENTAL)
    # Absolute paths: a search, even with BEFORE, finds a stray in core/ first.
    target_compile_definitions(pylatkmc_lib PRIVATE
        "PT_REACH_TEMPLATE_HEADER=\"${_inc_reach_h}\""
        "PYLATKMC_BUILD_INFO_HEADER=\"${_inc_info_h}\"")
    if(PYLATKMC_REPLAY_ORDER)
        target_compile_definitions(pylatkmc_lib PUBLIC PYLATKMC_REPLAY_ORDER)
    endif()
    if(PYLATKMC_INCREMENTAL_ORACLE)
        target_compile_definitions(pylatkmc_lib PUBLIC
            PYLATKMC_INCREMENTAL_ORACLE
            PYLATKMC_ORACLE_EVERY=${PYLATKMC_ORACLE_EVERY})
    endif()

    add_custom_command(TARGET pylatkmc_${MODEL} POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -DMODE=manifest "-DBINARY=$<TARGET_FILE:pylatkmc_${MODEL}>"
                -P "${_inc_script}"
        VERBATIM)
endif()

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
