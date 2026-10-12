# Minimal CMake package config for the Boost libraries cross-built by the
# Freetz "boost" package (Boost 1.87.0).
#
# CMake 4.x removed the FindBoost module, therefore projects that ask for
#   find_package(Boost CONFIG REQUIRED COMPONENTS thread)
# need a BoostConfig.cmake in the (staging) prefix. This file provides the
# include directories plus the components the Freetz package actually builds:
# thread and system.
#
# Installed as:
#   <prefix>/lib/cmake/Boost-1.87.0/BoostConfig.cmake
#   <prefix>/lib/cmake/Boost-1.87.0/boost_thread-config.cmake
#   <prefix>/lib/cmake/Boost-1.87.0/boost_system-config.cmake

get_filename_component(_boost_cmake_dir "${CMAKE_CURRENT_LIST_DIR}" ABSOLUTE)
get_filename_component(_boost_prefix "${_boost_cmake_dir}/../../.." ABSOLUTE)

set(Boost_VERSION 1.87.0)
set(Boost_VERSION_STRING "1.87.0")
set(Boost_INCLUDE_DIR "${_boost_prefix}/include")
set(Boost_INCLUDE_DIRS "${Boost_INCLUDE_DIR}")
set(Boost_LIBRARY_DIR "${_boost_prefix}/lib")
set(Boost_LIBRARY_DIRS "${Boost_LIBRARY_DIR}")

if(NOT TARGET Boost::headers)
  add_library(Boost::headers INTERFACE IMPORTED)
  set_target_properties(Boost::headers PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIR}")
endif()

if(NOT TARGET Boost::boost)
  add_library(Boost::boost INTERFACE IMPORTED)
  set_target_properties(Boost::boost PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIR}")
endif()

set(Boost_FOUND TRUE)

foreach(_boost_component ${Boost_FIND_COMPONENTS})
  set(_boost_component_config "${_boost_cmake_dir}/boost_${_boost_component}-config.cmake")
  if(EXISTS "${_boost_component_config}")
    include("${_boost_component_config}")
  else()
    set(Boost_${_boost_component}_FOUND FALSE)
    if(Boost_FIND_REQUIRED_${_boost_component})
      set(Boost_FOUND FALSE)
      set(Boost_NOT_FOUND_MESSAGE "Boost component '${_boost_component}' is not provided by the Freetz boost package (only thread and system are built)")
    endif()
  endif()
endforeach()

set(Boost_LIBRARIES "")
foreach(_boost_component ${Boost_FIND_COMPONENTS})
  if(TARGET Boost::${_boost_component})
    list(APPEND Boost_LIBRARIES Boost::${_boost_component})
  endif()
endforeach()

unset(_boost_component)
unset(_boost_component_config)
unset(_boost_cmake_dir)
unset(_boost_prefix)
