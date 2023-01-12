# Step 0: Make sure required repositories are installed (see README)

# Step 1: Build test cases (libsodium, HACL*) for five cases:
#   - unmitigated
#   - silent store only
#   - comp simp only
#   - silent store, then comp simp
#   - comp simp, then silent store

# Step 1a: (For each case) combine generated libsodium object files into single .o
# and rebuild with our wrapper

# Step 2: (For each case) run tests

