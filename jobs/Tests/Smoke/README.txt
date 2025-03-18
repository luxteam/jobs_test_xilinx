For every test case you can specify "ref_values" dictionary. If there's no "ref_values" for the test case then the case will succeed if FFmpeg command just finish normally without any errors.
When "ref_values" are specified, the output video will be checked to meet those reference values and the test case succeeds if all reference vales are met.

Full list of parameters which can be specified for reference are listed in class StreamInfo in jobs_test_xilinx\jobs\Scripts\run_tests.py.
Each parameter in "ref_values" has type which says how to interpret the value specified.
Possible types are:
equal - value taken from output stream must be equal to the specified
range - value taken from output stream must be in specified range, the range may be as a singe number and it's considered as the output value must be greater than reference
input - value taken from output stream must be equal to the same value taken from input stream, it fails if the value is absent in the input stream
skip - do not check specified parameter

The special member in "ref_values" called "default_type" sets the type of all parameters that are not specified explicitly. It may be set only to "input" or "skip".

See "compare_to_refs" function in jobs_test_xilinx\jobs\Scripts\run_tests.py for the algorithm cheching reference values.


General guide where to get reference values for a new test:
You can run test case manually, and evaluate its results by your eyes. Check visual quality, check output stream info meets expectations.
To get stream ifno you can use Mediainfo CLI tool:
mediainfo.exe -f stream_name
To get quality metrics run ffmpeg built with --enable-libvmaf, such ffmpeg can be downloaded from official website
ffmpeg_vmaf -i output.mp4 -i input.mp4 -filter_complex "ssim;[0:v][1:v]psnr;[0:v][1:v]libvmaf" -f null -
If manual test is ok, then the data from mediainfo and quality metrics can be taken as references.

If test case has some parameters explicitly passed as FFmpeg argument (e.g framerate), these parameters should be specified for reference.

