# Boost.System component, cross-built by the Freetz "boost" package.
# Included from BoostConfig.cmake (which defines Boost_INCLUDE_DIR and
# Boost_LIBRARY_DIR); the fallback below allows including this file directly.

if(NOT DEFINED Boost_LIBRARY_DIR)
  get_filename_component(_boost_system_cmake_dir "${CMAKE_CURRENT_LIST_DIR}" ABSOLUTE)
  get_filename_component(Boost_LIBRARY_DIR "${_boost_system_cmake_dir}/../.." ABSOLUTE)
endif()

set(Boost_system_LIBRARY "${Boost_LIBRARY_DIR}/libboost_system.so.1.87.0")

if(EXISTS "${Boost_system_LIBRARY}")
  if(NOT TARGET Boost::system)
    add_library(Boost::system SHARED IMPORTED)
    set_target_properties(Boost::system PROPERTIES
      IMPORTED_LOCATION "${Boost_system_LIBRARY}"
      INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIR}")
  endif()
  set(Boost_system_FOUND TRUE)
else()
  set(Boost_system_FOUND FALSE)
endif()

set(Boost_system_VERSION "1.87.0")

unset(_boost_system_cmake_dir)
