#!/bin/bash
FILE_FILTER=$1
TESTS_FILTER="$2"
TOOLS="$3"

python3.9 -m pip install -r ../jobs_launcher/install/requirements.txt

python3.9 ../jobs_launcher/executeTests.py \
    --test_filter $TESTS_FILTER \
    --file_filter $FILE_FILTER \
    --tests_root ../jobs \
    --work_root ../Work/Results \
    --work_dir Xilinx \
    --cmd_variables ResPath "." toolPath "../Xilinx" retries 2 tools $TOOLS
