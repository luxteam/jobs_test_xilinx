import re
from subprocess import check_output, STDOUT, CalledProcessError
from typing import Dict, Set, Any

from jobs_launcher.core.config import main_logger

def run_executable(command):
    main_logger.debug(f"Run command {command}")
    success = False
    try:
        output = check_output(
            command, stderr=STDOUT
        ).decode()
        success = True
    except CalledProcessError as e:
        output = e.output.decode()
    except Exception as e:
        output = str(e)

    return (success, output)


STREAM_INFO = {
    "width": 0,
    "height" : 0,
    "size": 0,
    "bitrate": 0,
    "num_frames": 0,
    "fps": 0,
    "gop_size": 0,
    "color_primaries" : "",
    "color_space": "",
    "subsampling": "",
    "bit_depth": 0,
    "psnr": 0,
    "ssim": 0,
    "vmaf": 0
}


def fill_stream_info(mediainfo, stream, info: Dict[str, Any]):
    success, output = run_executable([mediainfo, "-f", stream])

    if success:
        # cut off general info
        match = re.search(r"Video\s*\r\n", output)
        output = output[match.start():]

        # extract data
        match = re.search(r"Width.*\: (\d+)", output)
        if match is not None:
            info["width"] = int(match.group(1))

        match = re.search(r"Height.*\: (\d+)", output)
        if match is not None:
            info["height"] = int(match.group(1))

        match = re.search(r"Stream size.*\: (\d+)", output)
        if match is not None:
            info["size"] = int(match.group(1))

        match = re.search(r"Bit rate.*\: (\d+)", output)
        if match is not None:
            info["bitrate"] = int(match.group(1))

        match = re.search(r"Frame count.*\: (\d+)", output)
        if match is not None:
            info["num_frames"] = int(match.group(1))

        match = re.search(r"Frame rate.*\: ([\d,\.]+)", output)
        if match is not None:
            info["fps"] = float(match.group(1))

        match = re.search(r"Format settings, GOP.*N=(\d+)", output)
        if match is not None:
            info["gop_size"] = int(match.group(1))

        match = re.search(r"colour_primaries_Original.*\: ([\.,\w]+)", output)
        if match is not None:
            info["color_primaries"] = match.group(1)

        match = re.search(r"Color space.*\: (\w+)", output)
        if match is not None:
            info["color_space"] = match.group(1)

        match = re.search(r"Chroma subsampling.*\: ([\d,\:]+)", output)
        if match is not None:
            info["subsampling"] = match.group(1)

        match = re.search(r"Bit depth.*\: (\d+)", output)
        if match is not None:
            info["bit_depth"] = int(match.group(1))
    else:
        print("fill_stream_info failed")
        print(output)


def fill_stream_quality(ffmpeg, stream, ref_stream, info: Dict):
    # ffmpeg_vmaf -i output.mp4 -i input.mp4 -filter_complex "ssim;[0:v][1:v]psnr;[0:v][1:v]libvmaf" -f null -
    success, output = run_executable(
        [
            ffmpeg, "-i", stream, "-i", ref_stream, "-filter_complex",
            "ssim;[0:v][1:v]psnr;[0:v][1:v]libvmaf", "-f", "null", "-"
        ]
    )

    if success:
        match = re.search(r"PSNR.*average\:([\.,\d]+)", output)
        if match is not None:
            info["psnr"] = float(match.group(1))

        match = re.search(r"SSIM.*All\:([\.,\d]+)", output)
        if match is not None:
            info["ssim"] = float(match.group(1))

        match = re.search(r"VMAF score\: ([\.,\d]+)", output)
        if match is not None:
            info["vmaf"] = float(match.group(1))
    else:
        print("fill_stream_quality failed")
        print(output)

# ffmpeg.exe -y -i input.mp4 -usage 0 -profile:v 77 -quality 1 -rc cbr -b:v 125000 -g 30 -max_b_frames 3 -bf 3 -coder cabac -c:v h264_amf output.mp4
# ffmpeg.exe -y -i input.mp4 -usage 0 -profile:v 77 -quality 1 -rc cbr -b:v 125000 -minrate 50k -maxrate 1M -g 30 -max_b_frames 3 -bf 3 -coder cabac -c:v h264_amf output.mp4


# Keep this function consistent with jobs_test_xilinx\jobs\Tests\Smoke\README.txt
def compare_to_refs(stream_info: Dict, case, input_stream_info: Dict, error_messages: Set) -> bool:
    ref_values = case["ref_values"]
    default_type = ref_values["default_type"] if "default_type" in ref_values else "skip"

    for parameter, value in stream_info.items():
        if parameter in ref_values:
            ref_value = ref_values[parameter]

            if ref_value["type"] == "equal":
                if value != ref_value["value"]:
                    error_messages.add(f"{parameter} in output stream is {value} and isn't equal to {parameter} in original stream")
            elif ref_value["type"] == "range":
                range = ref_value["value"]
                if (value < range[0]) or (len(range) == 2 and value > range[1]):
                    error_messages.add(f"")
            elif ref_value["type"] == "input":
                if parameter not in input_stream_info or value != input_stream_info[parameter]:
                    error_messages.add(f"")
            elif ref_value["type"] == "skip":
                continue
        else:
            if default_type == "input":
                if parameter not in input_stream_info or value != input_stream_info[parameter]:
                    error_messages.add(f"")
            elif default_type == "skip":
                continue
