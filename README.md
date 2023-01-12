# Eval

## Required repositories
- Pandora LLVM: https://github.com/Flandini/llvm-project
- Checker: https://github.com/Flandini/checker
- Libsodium 1.0.18-stable: https://download.libsodium.org/libsodium/releases/

## Files
- `eval.py` (WIP): runs full eval
- `sac-llvm.py` (needs fixes): wrapper for building mitigated test cases. Intended to be a drop-in replacement for `clang`

## Data
We want eval data on:

[ ] test case runtime overhead with/without mitigations

[ ] checker runtime

[ ] compilation runtime with/without mitigations

[ ] pruning/ablation on checker features
