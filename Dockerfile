## Dockerfile for CIO evaluation

FROM ubuntu:22.04

## ----------------------------------------------------------------------------
## STEP 1: Install packages and dependencies
## ----------------------------------------------------------------------------

## Basic packages

RUN apt-get -y update && apt-get -y upgrade
RUN apt-get -y install sudo
RUN apt-get -y install git
RUN apt-get -y install python3

## LLVM dependencies

RUN apt-get -y install cmake
RUN apt-get -y install ninja-build
RUN apt-get -y install clang

## Checker dependencies

RUN apt-get -y install opam
RUN opam init --comp=4.14.1 -y
RUN opam install --confirm-level=unsafe-yes bap
RUN eval $(opam env)

## Offline verification dependencies




## ----------------------------------------------------------------------------
## STEP 2: Copy local files
## ----------------------------------------------------------------------------

RUN mkdir eval
WORKDIR /eval

## Copy checker directory
COPY checker ./checker/

## Copy build files
COPY Makefile .
COPY cio .
COPY checker_init .

## Copy basic test directory contents
COPY basictest/adder* ./basictest/
COPY basictest/test.c ./basictest/
COPY basictest/config.csv ./basictest/
COPY basictest/Makefile ./basictest/


## ----------------------------------------------------------------------------
## STEP 3: Install LLVM (project version and baseline)
## ----------------------------------------------------------------------------

## Get LLVM from remote
WORKDIR /
RUN git clone https://github.com/Flandini/llvm-project.git
RUN git clone llvm-project llvm-baseline

## Build project version
WORKDIR /llvm-project
RUN cmake -S llvm -B build -G Ninja -DLLVM_ENABLE_PROJECTS='clang'
RUN cd build && ninja
ENV LLVM_PROJECT=/llvm-project/build/bin/clang

## Build baseline version
WORKDIR /llvm-baseline
RUN git checkout baseline
RUN cmake -S llvm -B build -G Ninja -DLLVM_ENABLE_PROJECTS='clang'
RUN cd build && ninja
ENV CC=/llvm-baseline/build/bin/clang
WORKDIR /eval



