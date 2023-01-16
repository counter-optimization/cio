#!/bin/bash

if [[ ! -e bap_ld_scalar_mult.o ]]; then
    echo "Run jam_libsodium_together.sh first"
    exit 1
fi

LOOK_FOR_FUNCTIONS_WITH="scalarmult|25519|fe51|fe64"
OUTFILE=insns.txt

objdump --syms bap_ld_scalar_mult.o | grep -oP '(?<=F\s\.text\s[a-f0-9]{16})\s*\w+' | sed "s/\s//g" | grep -E "${LOOK_FOR_FUNCTIONS_WITH}" | xargs -I {} objdump -M suffix,no-aliases --no-show-raw-insn --no-addresses --disassemble={} bap_ld_scalar_mult.o >> $OUTFILE

# remove args
sed -i.bak "s/^\s*\([a-z]*\)\s*[^\s].*\s*/\1/" $OUTFILE

sort --unique $OUTFILE > unique_$OUTFILE
mv $OUTFILE.bak $OUTFILE

wc -l $OUTFILE unique_$OUTFILE
