# Boost.Thread component, cross-built by the Freetz "boost" package.
# Included from BoostConfig.cmake (which defines Boost_INCLUDE_DIR and
# Boost_LIBRARY_DIR); the fallback below allows including this file directly.

if(NOT DEFINED Boost_LIBRARY_DIR)
  get_filename_component(_boost_thread_cmake_dir "${CMAKE_CURRENT_LIST_DIR}" ABSOLUTE)
  get_filename_component(Boost_LIBRARY_DIR "${_boost_thread_cmake_dir}/../.." ABSOLUTE)
endif()

set(Boost_thread_LIBRARY "${Boost_LIBRARY_DIR}/libboost_thread.so.1.87.0")

if(EXISTS "${Boost_thread_LIBRARY}")
  if(NOT TARGET Boost::thread)
    add_library(Boost::thread SHARED IMPORTED)
    set_target_properties(Boost::thread PROPERTIES
      IMPORTED_LOCATION "${Boost_thread_LIBRARY}"
      INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIR}")
  endif()
  if(TARGET Boost::system)
    set_property(TARGET Boost::thread APPEND PROPERTY
      INTERFACE_LINK_LIBRARIES Boost::system)
  endif()
  set(Boost_thread_FOUND TRUE)
else()
  set(Boost_thread_FOUND FALSE)
endif()

set(Boost_thread_VERSION "1.87.0")

unset(_boost_thread_cmake_dir)
