# Run tests locally
To run tests locally please, setup environment variable `CIS_RENDER_DEVICE="MA35D"`, get ma35 samples in ./Xilinx folder using `./scripts/build_ma35_samples.sh`. Then run the `./scripts/run.sh` file with correct parameters.

A command to do all actions mentioned above:
```sh
    # from ./scripts
    export CIS_RENDER_DEVICE="MA35D" \
    chmod +x ./build_ma35_samples.sh \
    && ./build_ma35_samples.sh ../Xilinx \
    && chmod u+x ./run.sh \
    && ./run.sh "none" "<Test_Group_1> <Test_Group_2>" "<Tested_Tool>"
```
Please, note that the framework doesn't create a python virtual environment automatically. Instead it installs all the dependencies directly to system's Python.

## Script parameters
- Tested tools:
    - SimpleSamples - includes SimpleEncoder, SimpleDecoder, SimpleTranscoder, SimpleScaler
    - FFMPEG - includes only ffmpeg

- Test groups:
    - SimpleSamples tests:
        - Decoder_Main
        - Encoder_Full
        - Encoder_Main
        - Encoder_Smoke
        - Scaler
        - Transcoder
        - Transcoder_Main
    - FFMPEG tests:
        - FFMPEG_Multitranscode
        - FFMPEG_Teams
        - FFMPEG_Transcode

## Test results and artifacts
After test execution the Work folder will appear in the workspace. Most notable things in that folder are:
- Test session report (`./Work/Results/Xilinx/session_report.json`) - contains results of all test groups run during that session
- Test framework logs (`./Work/Results/Xilinx/launcher.engine.log`) - logs of test framework. It also may be found in `./scripts`
- Test group folder (`./Work/Results/Xilinx/<Test_Group>`) - contains specific test group results:
    - Color - folder with output artifacts video/streams/etc. For SimpleSamples all those artifacts are deleted after performing comparison to save space on test machines.
    - tool_logs - folder with .log and .html logs of running each test command. HTML versions created to be presented in [visual report](#Generate-visual-report)


## Generate visual report
To generate visual report you firstly need to copy the content of Work/Results to Xilinx_reports/MA35D-<OS_name>-<Test_Group>-<Tested_Tool> folder for the framework to work properly.
```sh
    # from jobs_launcher
    mkdir ../Xilinx_reports/MA35D-Ubuntu22-<Test_Group>-<Test_tool> \
    && cp -r ../Work/Results ../Xilinx_reports/MA35D-Ubuntu22-<Test_Group>-<Test_tool> \
    && chmod u+x ./build_reports.sh \
    && export CIS_RENDER_DEVICE="MA35D" \
    && ./build_reports.sh ../Xilinx_reports Xilinx <some_commit> <branch_name> "<commit_message>" "<Tested_Tool>"
```
After that open .`./Xilinx_reports/summary_report.html` in a browser to see the complete report.
