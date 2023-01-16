#!/bin/bash

# build libsodium as usual (don't do make install)
# run this script in the src/ dir

working_dir=$(pwd)
tmp1=$(echo "$working_dir" | grep -E '.+libsodium-stable/src$')
is_incorrect_working_dir=$?

if [[ $is_incorrect_working_dir ]]; then
    echo <<-EOF
    ran from wrong working dir	
EOF
    exit 1
fi

# exclude the './.libs/' dir that libsodium's build puts shared objects into
find ./libsodium/ -name '*.o' -a ! -path '*.libs*' | xargs ld -z muldefs -o bap_ld_scalar_mult.o -lc
exit 0
