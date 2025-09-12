# Commands to run
## Run tests locally
```sh
    # from ./scripts
    export CIS_RENDER_DEVICE="MA35D" \
    && ./run.sh "none" "<Test_Group>" "<Tested_Tool>"
```
Tested tools are "FFMPEG" or "SimpleSamples".
Test groups are names of the folders in jobs/Tests.

## Generate report
To generate report you firstly need to copy the content of Work/Results to Xilinx_reports/MA35D-<OS-name>-<Test_Group> folder for the framework to work properly
```sh
    # from jobs_launcher
    ./build_reports.sh ../Xilinx_reports Xilinx <some_commit> <branch_name> "<commit_message>" "<Tested_Tool>"
```
