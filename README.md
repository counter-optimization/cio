# Eval

## TODOs

- [ ] Write test files for crypto functions
  - [ ] AESNI-256-GCM
  - [ ] ChaCha20-Poly1305
  - [ ] Argon2id
  - [X] Ed25519 signing
- [ ] Get pipeline working w/out checker (no mitigations)
- [ ] Get pipeline working with choice of mitigations
- [ ] Automate running the pipeline for all cases
- [ ] Automate `.tex` output from raw eval data

## Required repositories
- Pandora LLVM: https://github.com/Flandini/llvm-project
- Checker: https://github.com/Flandini/checker
- Libsodium 1.0.18-stable: https://download.libsodium.org/libsodium/releases/

## Files
- `eval.py` (WIP): runs full eval
- `sac-llvm.py` (needs fixes): wrapper for building mitigated test cases. Intended to be a drop-in replacement for `clang`

## Data
We want eval data on:

- [ ] runtime overhead for crypto functions
  - with/without mitigations, ablated over different mitigations

- [ ] checker runtime

- [ ] compilation runtime overhead with/without mitigations

- [ ] pruning/ablation on checker features

## Pipeline

- [ ] Compile crypto libraries
  - [ ] libsodium
    - [ ] with mitigations
    - [ ] without mitigations
  - [ ] HACL*
    - [ ] with mitigations
    - [ ] without mitigations
  - [ ] Ablate compilations across...
    - [ ] Silent store
    - [ ] Comp simp categories (final list TBD)
      - [ ] All arithmetic ops?
      - [ ] All bitwise ops?
      - [ ] Shifts only?
      - [ ] `mul` only?
- [ ] Run checker on compiled libraries
  - [ ] libsodium
    - [ ] with mitigations
    - [ ] without mitigations
  - [ ] HACL*
    - [ ] with mitigations
    - [ ] without mitigations
- [ ] Evaluate on crypto functions (final list TBD) 
  - [ ] run `make` to do all of this
  - [ ] AESNI-256-GCM
  - [ ] ChaCha20-Poly1305
  - [ ] Argon2id
  - [X] Ed25519 signing
- [ ] Output final data to LaTeX
