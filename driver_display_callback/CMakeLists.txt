cmake_minimum_required(VERSION 3.5)
project(barnold_display_callback)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

#set(CMAKE_BUILD_TYPE DEBUG)
set(CMAKE_BUILD_TYPE RELEASE)

set(SOURCE_FILES
    src/driver_display_callback.cpp
    )

# Sorry, this is hardcoded
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake/modules/")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -fPIC -Wno-narrowing")

find_package(Arnold REQUIRED)

get_filename_component(ArnLib ${ARNOLD_LIBRARIES} DIRECTORY )
message(${ArnLib})

include_directories(${ARNOLD_INCLUDE_DIRS})
link_directories(${ArnLib})

add_library(${PROJECT_NAME} SHARED ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} ${ARNOLD_LIBRARIES})


