# Commands to run
## Run tests locally
```sh
    # from ./scripts
    export CIS_RENDER_DEVICE="MA35D" \
    && chmod u+x ./run.sh \
    && ./run.sh "none" "<Test_Group_1> <Test_Group_2>" "<Tested_Tool>"
```
Tested tools are "FFMPEG" or "SimpleSamples".
Test groups are names of the folders in jobs/Tests.

## Generate report
To generate report you firstly need to copy the content of Work/Results to Xilinx_reports/MA35D-<OS_name>-<Test_Group>-<Tested_Tool> folder for the framework to work properly
```sh
    # from jobs_launcher
    mkdir ../Xilinx_reports/MA35D-Ubuntu22-<Test_Group>-<Test_tool> \
    && cp -r ../Work/Results ../Xilinx_reports/MA35D-Ubuntu22-<Test_Group>-<Test_tool> \
    && chmod u+x ./build_reports.sh \
    && ./build_reports.sh ../Xilinx_reports Xilinx <some_commit> <branch_name> "<commit_message>" "<Tested_Tool>"
```
After that open ../Xilinx_reports/summary_report.html in a browser to see the complete report.

## Available test groups
### SimpleSamples tests
- Decoder_Main
- Encoder_Full
- Encoder_Main
- Encoder_Smoke
- Scaler
- Transcoder
- Transcoder_Main

### FFMPEG tests
- FFMPEG_Multitranscode
- FFMPEG_Teams
- FFMPEG_Transcode