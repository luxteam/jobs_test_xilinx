import json
import os
import platform
import re
from subprocess import Popen, PIPE, check_output, STDOUT, CalledProcessError
import time
import traceback
from datetime import datetime
from shutil import copyfile

from utils import is_case_skipped

from jobs_launcher.common.scripts.script_info_by_platform import get_script_info  # noqa
from jobs_launcher.common.scripts.status_by_platform import get_status
from jobs_launcher.core.config import (CASE_REPORT_SUFFIX, RENDER_REPORT_BASE,
                                       VIDEO_KEY, main_logger)
from jobs_launcher.core.system_info import get_gpu


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


class StreamInfo:
    width           : int = 0
    height          : int = 0
    size            : int = 0
    bitrate         : int = 0
    num_frames      : int = 0
    fps             : float = 0
    gop_size        : int = 0
    color_primaries : str = ""
    color_space     : str = ""
    subsampling     : str = ""
    bit_depth       : int = 0


class StreamQuality:
    psnr : int = 0
    ssim : int = 0
    vmaf : int = 0


def fill_stream_info(mediainfo, stream, info: StreamInfo):
    success, output = run_executable([mediainfo, "-f", stream])

    if success:
        # cut off general info
        match = re.search(r"Video\s*\r\n", output)
        output = output[match.start():]

        # extract data
        match = re.search(r"Width.*\: (\d+)", output)
        if match is not None:
            info.width = match.group(1)

        match = re.search(r"Height.*\: (\d+)", output)
        if match is not None:
            info.height = match.group(1)

        match = re.search(r"Stream size.*\: (\d+)", output)
        if match is not None:
            info.size = match.group(1)

        match = re.search(r"Bit rate.*\: (\d+)", output)
        if match is not None:
            info.bitrate = match.group(1)

        match = re.search(r"Frame count.*\: (\d+)", output)
        if match is not None:
            info.num_frames = match.group(1)

        match = re.search(r"Frame rate.*\: ([\d,\.]+)", output)
        if match is not None:
            info.fps = match.group(1)

        match = re.search(r"Format settings, GOP.*N=(\d+)", output)
        if match is not None:
            info.gop_size = match.group(1)

        match = re.search(r"colour_primaries_Original.*\: ([\.,\w]+)", output)
        if match is not None:
            info.color_primaries = match.group(1)

        match = re.search(r"Color space.*\: (\w+)", output)
        if match is not None:
            info.color_space = match.group(1)

        match = re.search(r"Chroma subsampling.*\: ([\d,\:]+)", output)
        if match is not None:
            info.subsampling = match.group(1)

        match = re.search(r"Bit depth.*\: (\d+)", output)
        if match is not None:
            info.bit_depth = match.group(1)
    else:
        print("fill_stream_info failed")
        print(output)


def fill_stream_quality(ffmpeg, stream, ref_stream, quality: StreamQuality):
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
            quality.psnr = match.group(1)

        match = re.search(r"SSIM.*All\:([\.,\d]+)", output)
        if match is not None:
            quality.ssim = match.group(1)

        match = re.search(r"VMAF score\: ([\.,\d]+)", output)
        if match is not None:
            quality.vmaf = match.group(1)
    else:
        print("fill_stream_quality failed")
        print(output)

# ffmpeg.exe -y -i input.mp4 -usage 0 -profile:v 77 -quality 1 -rc cbr -b:v 125000 -g 30 -max_b_frames 3 -bf 3 -coder cabac -c:v h264_amf output.mp4
# ffmpeg.exe -y -i input.mp4 -usage 0 -profile:v 77 -quality 1 -rc cbr -b:v 125000 -minrate 50k -maxrate 1M -g 30 -max_b_frames 3 -bf 3 -coder cabac -c:v h264_amf output.mp4


def prepare_keys(case: dict, input_stream: str, output_stream: str) -> str:
    keys: str = case["ffmpeg_parameters"]
    keys = keys.replace("<input_stream>", input_stream)
    keys = keys.replace("<output_stream>", output_stream)
    return keys


def execute_tests(args, current_conf):
    rc = 0
    test_cases_path = os.path.join(os.path.abspath(args.output), "test_cases.json")
    with open(test_cases_path, "r") as json_file:
        cases = json.load(json_file)

    logs_path = os.path.abspath(os.path.join(args.output, "tool_logs"))
    ffmpeg_path = os.path.abspath(os.path.join(args.tool_path, "ffmpeg.exe"))  # noqa
    ffmpeg_vmaf_path = os.path.abspath(os.path.join(args.tool_path, "ffmpeg_vmaf.exe"))  # noqa
    mediainfo_path = os.path.abspath(os.path.join(args.tool_path, "MediaInfo.exe"))  # noqa
    previous_case = None

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:
        output_path = os.path.abspath(os.path.join(args.output, "Color", case["case"]))
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        input_stream = os.path.abspath(os.path.join(args.tool_path, "input.mp4"))
        output_stream = os.path.join(output_path, f"{case['case']}.mp4")
        main_logger.debug(f"input stream: {input_stream}")
        main_logger.debug(f"output stream: {output_stream}")
        reference_stream = input_stream

        case_start_time = time.time()
        current_try = 0

        max_tries = args.retries
        # ask Ilia about logic
        # if previous_case and set(CHAIN_OF_CASES_KEYS) & set(previous_case.keys()):
        #     max_tries = 1

        while current_try < max_tries:
            main_logger.info(
                f"Start test case {case['case']}. Try: {current_try}"
            )
            error_messages = set()

            try:
                prepared_keys = prepare_keys(case, input_stream, output_stream)
                case["prepared_keys"] = prepared_keys
                keys_description = f"FFmpeg parameters: {prepared_keys}"
                case["script_info"].append(keys_description)
                main_logger.debug(keys_description)

                command = prepared_keys.split()
                # ffmpeg.exe -y -i input.mp4 -c:v h264_amf output.mp4
                command.insert(0, ffmpeg_path)
                # иметь процесс в отдельной переменной -- хорошая идея,
                # тк иногда у нас в прогонах для зайлинкса застревали всякие декодеры

                # main logic
                log = os.path.join(logs_path, f"{case['case']}.log")
                with open(log, "w+") as file:
                    # TODO: set timeout for process
                    Popen(command, stderr=file.fileno(), stdout=file.fileno()).wait()
                execution_time = time.time() - case_start_time

                # read log
                with open(log, "r") as file:
                    log_content = file.read()

                # check the log on errors
                if "error" in log_content.lower():
                    raise Exception(f"FFmpeg failed to process command: {prepared_keys}")

                # results processing
                info = StreamInfo()
                quality = StreamQuality()
                fill_stream_info(mediainfo_path, output_stream, info)
                fill_stream_quality(ffmpeg_vmaf_path, output_stream, input_stream, quality)

                main_logger.debug(str(info.__dict__))
                main_logger.debug(str(quality.__dict__))

                save_results(args, case, cases, execution_time=execution_time, test_case_status="passed", error_messages=error_messages)
                break
            except Exception as e:
                execution_time = time.time() - case_start_time
                test_case_status = "failed"
                if case["status"] == "observed":
                    test_case_status = case["status"]

                save_results(args, case, cases, execution_time=execution_time, test_case_status=test_case_status, error_messages=error_messages)

                main_logger.error("Failed to execute test case (try #{}): {}".format(current_try, str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
            finally:
                current_try += 1
                main_logger.info("End of test case")
        else:
            main_logger.error("Failed to execute case '{}' at all".format(case["case"]))
            rc = -1
            execution_time = time.time() - case_start_time
            test_case_status = "failed"
            if case["status"] == "observed":
                test_case_status = case["status"]
            save_results(args, case, cases, execution_time=execution_time, test_case_status=test_case_status, error_messages=error_messages)
            previous_case = case

    return rc


def copy_test_cases(args):
    try:
        test_cases_path = os.path.realpath(
            os.path.join(
                os.path.dirname(__file__), '..', 'Tests',
                args.test_group, 'test_cases.json'
            )
        )
        test_cases_copy = os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json')
        )
        main_logger.debug(f"test_cases_copy path: {test_cases_copy}")

        copyfile(test_cases_path, test_cases_copy)

        # check if it is needed
        # cases = json.load(open(test_cases_copy))

        with open(test_cases_copy, "r") as json_file:
            cases = json.load(json_file)

        if os.path.exists(args.test_cases) and args.test_cases:
            with open(args.test_cases) as file:
                test_cases = json.load(file)['groups'][args.test_group]
                if test_cases:
                    necessary_cases = [
                        item for item in cases if item['case'] in test_cases
                    ]
                    cases = necessary_cases

            output_cases = os.path.join(args.output, 'test_cases.json')
            main_logger.debug(f"output_cases path: {output_cases}")
            with open(output_cases, "w+") as file:
                json.dump(cases, file, indent=4)

    except Exception as e:
        main_logger.error('Can\'t load test_cases.json')
        main_logger.error(str(e))
        exit(-1)


def prepare_empty_reports(args, current_conf):
    main_logger.info('Create empty report files')

    test_cases = os.path.join(os.path.abspath(args.output), "test_cases.json")

    with open(test_cases, "r") as json_file:
        cases = json.load(json_file)

    for case in cases:
        if is_case_skipped(case, current_conf):
            case['status'] = 'skipped'

        if "status_by_platform" in case:
            case["status"] = get_status(case)

        if "script_info_by_platform" in case:
            case["script_info"] = get_script_info(case)

        if case['status'] != 'done' and case['status'] != 'error':
            if case["status"] == 'inprogress':
                case['status'] = 'active'
            elif case["status"] == 'inprogress_observed':
                case['status'] = 'observed'

            test_case_report = RENDER_REPORT_BASE.copy()
            test_case_report['test_case'] = case['case']
            # test_case_report['render_device'] = get_gpu()
            test_case_report['script_info'] = case['script_info']
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'Xilinx'
            test_case_report['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S'
            )

            if case['status'] == 'skipped':
                test_case_report['test_status'] = 'skipped'
                test_case_report['group_timeout_exceeded'] = False
            else:
                test_case_report['test_status'] = 'error'

            case_path = os.path.join(
                args.output, case['case'] + CASE_REPORT_SUFFIX
            )

            with open(case_path, "w") as f:
                f.write(json.dumps([test_case_report], indent=4))

    with open(os.path.join(args.output, "test_cases.json"), "w+") as f:
        json.dump(cases, f, indent=4)


def save_results(args, case, cases, execution_time=0.0, test_case_status="", error_messages=[]):

    case_report_path = os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX)
    with open(case_report_path, "r") as file:
        test_case_report = json.loads(file.read())[0]

    test_case_report["execution_time"] = execution_time
    test_case_report["log"] = os.path.join("tool_logs", case["case"])

    test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    test_case_report["number_of_tries"] += 1

    test_case_report["message"] = test_case_report["message"] + list(error_messages)

    test_case_report["ffmpeg_parameters"] = case["prepared_keys"]

    if test_case_report["test_status"] in ["passed", "observed", "error"]:
        test_case_report["group_timeout_exceeded"] = False

    video_path = os.path.join("Color", case["case"] + "win_client.mp4")
    if os.path.exists(os.path.join(args.output, video_path)):
        test_case_report[VIDEO_KEY] = video_path

    test_case_report["script_info"] = case["script_info"]

    if "expected_behaviour" in case:
        test_case_report["expected_behaviour"] = case["expected_behaviour"]

    with open(case_report_path, "w") as file:
        json.dump([test_case_report], file, indent=4)

    if test_case_status:
        case["status"] = test_case_status

    with open(os.path.join(args.output, "test_cases.json"), "w") as file:
        json.dump(cases, file, indent=4)


def run_tests(args):
    main_logger.info('run_tests starts working...')
    main_logger.info(f'tests run with following args: {args}')

    try:
        if not os.path.exists(os.path.join(args.output, "Color")):
            os.makedirs(os.path.join(args.output, "Color"))

        if not os.path.exists(os.path.join(args.output, "tool_logs")):
            os.makedirs(os.path.join(args.output, "tool_logs"))

        render_device = get_gpu()
        system_pl = platform.system()
        current_conf = set(system_pl) if not render_device else {system_pl, render_device}
        main_logger.info("Detected GPUs: {}".format(render_device))
        main_logger.info("PC conf: {}".format(current_conf))
        main_logger.info("Creating predefined errors json...")

        copy_test_cases(args)
        prepare_empty_reports(args, current_conf)
        exit(execute_tests(args, current_conf))
    except Exception as e:
        main_logger.error(
            "Failed during script execution. Exception: {}".format(str(e))
        )
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        exit(-1)
