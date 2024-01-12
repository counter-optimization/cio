## Dockerfile for CIO evaluation

FROM ubuntu:22.04

## ----------------------------------------------------------------------------
## STEP 1: Initial set up
## ----------------------------------------------------------------------------

## Install basic packages
RUN apt-get -y update && apt-get -y upgrade && \
    apt-get -y install sudo && \
    apt-get -y install git && \
    apt-get -y install python3

## Install LLVM dependencies
RUN apt-get -y install cmake && \
    apt-get -y install ninja-build && \
    apt-get -y install clang

## Install checker dependencies

RUN apt-get -y install opam && \
    opam init --comp=4.14.1 -y && \
    opam install --confirm-level=unsafe-yes bap z3

## Create working directory
RUN mkdir eval
WORKDIR /eval

## ----------------------------------------------------------------------------
## STEP 2: Install clang (project version and baseline)
## ----------------------------------------------------------------------------

## Build clang all in one step so we can delete excess files afterward
RUN git clone https://github.com/Flandini/llvm-project.git && \
    cd llvm-project && \
    cmake -S llvm -B build -G Ninja -DLLVM_ENABLE_PROJECTS='clang' && \
    cd build && ninja && \
    cp bin/clang /eval/clang && \
    cd /eval && rm -rf llvm-project
ENV PROJECT_CC=/eval/clang

# RUN git clone llvm-project llvm-baseline

# ## Build project version
# WORKDIR /llvm-project
# RUN cmake -S llvm -B build -G Ninja -DLLVM_ENABLE_PROJECTS='clang'
# RUN cd build && ninja
# ENV LLVM_PROJECT=/llvm-project/build/bin/clang

# ## Build baseline version
# WORKDIR /llvm-baseline
# RUN git checkout baseline
# RUN cmake -S llvm -B build -G Ninja -DLLVM_ENABLE_PROJECTS='clang'
# RUN cd build && ninja
# ENV CC=/llvm-baseline/build/bin/clang
# WORKDIR /eval


## ----------------------------------------------------------------------------
## STEP 3: Copy local files
## ----------------------------------------------------------------------------

## Set up checker directory
COPY checker ./checker/
RUN rm checker/bap/interval/uarch_checker.plugin && \
    ln -s /eval/checker/bap/interval/_build/uarch_checker.plugin \
        checker/bap/interval/uarch_checker.plugin

## Copy build files
COPY Makefile .
COPY cio .
COPY checker_init .

## Copy basic test
COPY basictest/*.c basictest/*.h basictest/config.csv basictest/Makefile \
    ./basictest/

CMD eval $(opam env) && make CC=$PROJECT_CC test
