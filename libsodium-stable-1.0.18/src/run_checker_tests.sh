make clean
cd test/comp-simp/
make
cd ../../
PYTHONPATH=/Users/mkf727/projects/checker:/Users/mkf727/projects/checker/test python3 test/comp-simp/comp_simp_test_runner.py
