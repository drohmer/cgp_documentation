# WebGL demos of the documentation: one CGP scene per folder of demos/, compiled with
# Emscripten. The CGP library is compiled once (static library) and linked by every demo.
#
# Each demo folder holds the files that differ from the cgp-2027 template project:
#   scene.hpp, scene.cpp (required), any other src/ file to replace, sub-folders of sources
#   (compiled recursively, as in the CGP projects), and optionally shaders/ (added to the
#   default shaders) and assets/.
# They are staged over a copy of cgp-2027/src and cgp-2027/shaders at configure time.
#
# Usage: see demos/build.py (emcmake cmake -S demos -B build/demos && cmake --build ...).
cmake_minimum_required(VERSION 3.16)
project(cgp_demos LANGUAGES CXX)

if(NOT EMSCRIPTEN)
    message(FATAL_ERROR "Configure with emcmake (Emscripten SDK)")
endif()

set(CGP_DIR "${CMAKE_CURRENT_LIST_DIR}/../../cgp-2027" CACHE PATH "cgp-2027 project")
set(DEMO_OUT "${CMAKE_CURRENT_LIST_DIR}/../content/assets" CACHE PATH "Output: <DEMO_OUT>/<name>-demo/")
set(DEMO_LIST "" CACHE STRING "Demos to build (empty = all)")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- CGP library, compiled once
file(GLOB_RECURSE CGP_SRC "${CGP_DIR}/cgp/*.cpp")
add_library(cgp STATIC ${CGP_SRC})
target_include_directories(cgp PUBLIC "${CGP_DIR}" "${CGP_DIR}/cgp")
target_compile_definitions(cgp PUBLIC
    SOLUTION CGP_OPENGL_3_3 IMGUI_IMPL_OPENGL_LOADER_GLAD CGP_ERROR_EXCEPTION CGP_NO_DEBUG)
target_compile_options(cgp PUBLIC -O2 -sUSE_GLFW=3 -Wno-pragmas)

# ---- One executable per demo
file(GLOB DEMO_DIRS LIST_DIRECTORIES true "${CMAKE_CURRENT_LIST_DIR}/*")
foreach(dir ${DEMO_DIRS})
    if(NOT EXISTS "${dir}/scene.cpp")
        continue()
    endif()
    get_filename_component(name "${dir}" NAME)
    if(DEMO_LIST AND NOT name IN_LIST DEMO_LIST)
        continue()
    endif()

    # Stage: template src/ and shaders/, then the files of the demo on top
    set(stage "${CMAKE_BINARY_DIR}/stage/${name}")
    file(REMOVE_RECURSE "${stage}")
    file(COPY "${CGP_DIR}/src/" DESTINATION "${stage}/src")
    file(COPY "${CGP_DIR}/shaders/" DESTINATION "${stage}/shaders")
    file(GLOB demo_files "${dir}/*.cpp" "${dir}/*.hpp")
    file(COPY ${demo_files} DESTINATION "${stage}/src")
    # sub-folders of sources (examples split in modules: implicit_surface/, multipass/...)
    file(GLOB demo_subdirs LIST_DIRECTORIES true "${dir}/*")
    foreach(sub ${demo_subdirs})
        get_filename_component(sub_name "${sub}" NAME)
        if(IS_DIRECTORY "${sub}" AND NOT sub_name MATCHES "^(assets|shaders|__pycache__)$")
            file(COPY "${sub}" DESTINATION "${stage}/src")
        endif()
    endforeach()
    if(EXISTS "${dir}/shaders")
        file(COPY "${dir}/shaders/" DESTINATION "${stage}/shaders")
    endif()
    # Re-run the configuration when a file of the demo changes
    file(GLOB_RECURSE watched "${dir}/*")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${watched})

    file(GLOB_RECURSE stage_src "${stage}/src/*.cpp")
    set(target "demo_${name}")
    add_executable(${target} ${stage_src})
    target_include_directories(${target} PRIVATE "${stage}/src")
    target_link_libraries(${target} PRIVATE cgp)
    set(out "${DEMO_OUT}/${name}-demo")
    set_target_properties(${target} PROPERTIES
        OUTPUT_NAME project SUFFIX ".js" RUNTIME_OUTPUT_DIRECTORY "${out}")
    target_link_options(${target} PRIVATE
        -sMAX_WEBGL_VERSION=2 -sUSE_GLFW=3 -sALLOW_MEMORY_GROWTH=1 -O2
        "SHELL:--preload-file ${stage}/shaders@shaders/")   # SHELL: else CMake merges repeated flags
    if(EXISTS "${dir}/assets")
        target_link_options(${target} PRIVATE "SHELL:--preload-file ${dir}/assets@assets/")
    endif()
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_LIST_DIR}/index.html" "${out}/index.html")
endforeach()
