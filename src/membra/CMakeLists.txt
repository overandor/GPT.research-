cmake_minimum_required(VERSION 3.16)
project(overandor_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(overandor_engine overandor_engine.cpp)

# This target is intentionally self-contained for buyer/auditor diligence.
# It performs deterministic review logic and emits a JSON-style audit event.
