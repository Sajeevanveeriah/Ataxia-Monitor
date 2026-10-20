cmake_minimum_required(VERSION 3.16)
# Keep the acquisition image and its dependencies only. Including every IDF
# component makes the Windows linker-script command exceed the shell limit.
set(COMPONENTS touch_app __pio_env)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(vw_mtc1_touch)
