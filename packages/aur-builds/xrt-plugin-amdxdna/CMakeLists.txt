cmake_minimum_required(VERSION 3.22)
project(xrt_driver_xdna LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(SHIM_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/xdna-driver/src/shim")
set(XRT_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/XRT/src/runtime_src")

# Build only the userspace plugin, using the exact installed XRT source headers.
# Upstream's native CMake also builds XRT itself, which is already packaged.
file(GLOB shim_sources
  "${SHIM_SOURCE}/*.cpp"
  "${SHIM_SOURCE}/kmq/*.cpp"
  "${SHIM_SOURCE}/umq/*.cpp"
  "${SHIM_SOURCE}/host/*.cpp"
  "${SHIM_SOURCE}/virtio/*.cpp"
)
add_library(xrt_driver_xdna SHARED ${shim_sources})
target_compile_definitions(xrt_driver_xdna PRIVATE XRT_ENABLE_AIE XRT_AIE_BUILD XRT_BUILD)
target_include_directories(xrt_driver_xdna PRIVATE
  "${XRT_SOURCE}"
  "${XRT_SOURCE}/core/include"
  "${CMAKE_CURRENT_SOURCE_DIR}/GSL/include"
  "${SHIM_SOURCE}/../include/uapi"
  "${SHIM_SOURCE}/../vxdna/src"
)
target_link_libraries(xrt_driver_xdna PRIVATE xrt_core xrt_coreutil)
target_link_options(xrt_driver_xdna PRIVATE -Wl,-z,defs)
set_target_properties(xrt_driver_xdna PROPERTIES VERSION 2.25.0 SOVERSION 2)
install(TARGETS xrt_driver_xdna LIBRARY DESTINATION lib)
