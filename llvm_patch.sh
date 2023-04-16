
# fixups for invalid MIR serialized by LLVM
function inline_patch_mir_file {
    set -x

    BASENAME=$(basename "$1")
    echo "BASENAME is $BASENAME"
    if [[ "$BASENAME" == "libsse2_la-poly1305_sse2.indexed.mir" ]]; then
	echo "inline patching file: $1"
	sed -i'' 's/<4 x i32> zeroinitializer/<4 x i32> <i32 0, i32 0, i32 0, i32 0>/gi' "$1"
	
	SED_RES=$?
	if [[ $SED_RES -ne 0 ]]; then
	    echo "sed for zeroinitializer failed"
	    exit $SED_RES
	fi
    fi
    
    # ibsse2_la-poly1305_sse2.indexed.mir
    # libsse2_la-poly1305_sse2.indexed.mir
    if [[ "$BASENAME" == "libsse2_la-poly1305_sse2.mir" ]]; then
	echo "inline patching file: $1"
	sed -i'' 's/<4 x i32> zeroinitializer/<4 x i32> <i32 0, i32 0, i32 0, i32 0>/gi' "$1"
	
	SED_RES=$?
	if [[ $SED_RES -ne 0 ]]; then
	    echo "sed for zeroinitializer failed"
	    exit $SED_RES
	fi
    fi

    grep -Ei 'renamable (\$xmm14|\$xmm15)' "$1"
    GREP_RES=$?
    # if $GREP_RES -eq 0, then there was a line that matched
    if [[ $GREP_RES -eq 0 ]]; then
	echo "Editing file $1 to remove renamable attribute of reserved register"
	sed -E -i'' 's/renamable (\$xmm14|\$xmm15)/\1/gi' "$1"
    fi
}
