import json
import os
import platform
import time
import traceback
from copy import deepcopy
from datetime import datetime
from subprocess import Popen
from shutil import copyfile

from process_results import (fill_stream_info, fill_stream_quality,
                             compare_to_refs, STREAM_INFO)
from utils import is_case_skipped, save_logs

from jobs_launcher.common.scripts.script_info_by_platform import get_script_info  # noqa: E501
from jobs_launcher.common.scripts.status_by_platform import get_status
from jobs_launcher.core.config import (CASE_REPORT_SUFFIX, VIDEO_KEY,
                                       main_logger)
from jobs_launcher.core.system_info import get_gpu


def execute_tests(args, current_conf):
    rc = 0
    test_cases_path = os.path.join(os.path.abspath(args.output), "test_cases.json")  # noqa: E501
    with open(test_cases_path, "r") as json_file:
        cases = json.load(json_file)

    logs_path = os.path.join(args.output, "tool_logs")
    ffmpeg_path = os.path.join(args.tool_path, "ffmpeg.exe")
    ffmpeg_vmaf_path = os.path.join(args.tool_path, "ffmpeg_vmaf.exe")
    mediainfo_path = os.path.join(args.tool_path, "MediaInfo.exe")

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:
        output_path = os.path.join(args.output, "Color")
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        input_stream = os.path.join(args.tool_path, "input.mp4")
        output_stream = os.path.relpath(os.path.join(output_path, f"{case['case']}.mp4"))  # noqa: E501
        main_logger.debug(f"input stream: {input_stream}")
        main_logger.debug(f"output stream: {output_stream}")

        case_start_time = time.time()
        current_try = 0

        max_tries = args.retries

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

                command = [ffmpeg_path,] + prepared_keys.split()

                # main logic
                ffmpeg_log = os.path.join(logs_path, f"{case['case']}.log")
                with open(ffmpeg_log, "w+") as file:
                    # TODO: set timeout for process
                    Popen(command, stderr=file.fileno(), stdout=file.fileno()).wait()  # noqa: E501
                execution_time = time.time() - case_start_time

                # read log
                with open(ffmpeg_log, "r") as file:
                    log_content = file.read()
                    # rewrite as html like in streaming tests

                # check the log on errors
                if "error" in log_content.lower():
                    raise Exception(f"FFmpeg failed to process command: {prepared_keys}")  # noqa: E501

                # results processing
                output_stream_params = deepcopy(STREAM_INFO)
                input_stream_params = deepcopy(STREAM_INFO)

                fill_stream_info(mediainfo_path, input_stream,
                                 input_stream_params)
                main_logger.debug(f"Input stream data: {input_stream_params}")
                fill_stream_info(mediainfo_path, output_stream,
                                 output_stream_params)
                fill_stream_quality(ffmpeg_vmaf_path, output_stream,
                                    input_stream, output_stream_params)

                case["input_stream_params"] = input_stream_params
                case["output_stream_params"] = output_stream_params

                compare_to_refs(output_stream_params, case,
                                input_stream_params, error_messages)

                save_logs(args, case, ffmpeg_log)
                test_case_status = "passed"
                if error_messages:
                    test_case_status = "failed"

                save_results(args, case, cases,
                             execution_time=execution_time,
                             test_case_status=test_case_status,
                             error_messages=error_messages)
                break
            except Exception as e:
                execution_time = time.time() - case_start_time

                save_logs(args, case, ffmpeg_log)

                test_case_status = "failed"
                if case["status"] == "observed":
                    test_case_status = case["status"]

                save_results(args, case, cases,
                             execution_time=execution_time,
                             test_case_status=test_case_status,
                             error_messages=error_messages)

                main_logger.error(f"Failed to execute test case (try #{current_try}): {str(e)}")  # noqa: E501
                main_logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                current_try += 1
                main_logger.info("End of test case")
        else:
            case_name = case["case"]
            main_logger.error(f"Failed to execute case '{case_name}' at all")
            rc = -1
            execution_time = time.time() - case_start_time
            test_case_status = "failed"
            if case["status"] == "observed":
                test_case_status = case["status"]
            save_results(args, case, cases,
                         execution_time=execution_time,
                         test_case_status=test_case_status,
                         error_messages=error_messages)

    return rc


def copy_test_cases(args):
    try:
        test_cases_path = os.path.realpath(
            os.path.join(
                os.path.dirname(__file__), '..', 'Tests',
                args.test_group, 'test_cases.json'
            )
        )
        test_cases_copy = os.path.realpath(os.path.join(os.path.abspath(args.output), 'test_cases.json'))  # noqa: E501
        main_logger.debug(f"test_cases_copy path: {test_cases_copy}")

        copyfile(test_cases_path, test_cases_copy)

        with open(test_cases_copy, "r") as json_file:
            cases = json.load(json_file)

        if os.path.exists(args.test_cases) and args.test_cases:
            with open(args.test_cases) as file:
                test_cases = json.load(file)['groups'][args.test_group]
                if test_cases:
                    necessary_cases = [item for item in cases if item['case'] in test_cases]  # noqa: E501
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

            test_case_report = {}
            test_case_report['render_time'] = 0.0
            test_case_report["number_of_tries"] = 0
            test_case_report["message"] = []
            test_case_report['render_device'] = get_gpu()

            test_case_report['test_case'] = case['case']
            test_case_report['script_info'] = case['script_info']
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'Xilinx'
            test_case_report['date_time'] = datetime.now().strftime('%m/%d/%Y %H:%M:%S')  # noqa: E501

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


def save_results(args, case, cases, execution_time=0.0, test_case_status="",
                 error_messages=[]):

    case_report_path = os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX)  # noqa: E501
    with open(case_report_path, "r") as file:
        test_case_report = json.loads(file.read())[0]

    test_case_report["execution_time"] = execution_time
    test_case_report["log"] = os.path.join("tool_logs", case["case"] + ".html")

    test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")  # noqa: E501
    test_case_report["number_of_tries"] += 1

    test_case_report["message"] = (test_case_report["message"] + list(error_messages))  # noqa: E501

    test_case_report["ffmpeg_parameters"] = case["prepared_keys"]
    test_case_report["input_stream_params"] = case["input_stream_params"]
    test_case_report["output_stream_params"] = case["output_stream_params"]
    test_case_report["test_status"] = test_case_status

    if test_case_report["test_status"] in ["passed", "observed", "error"]:
        test_case_report["group_timeout_exceeded"] = False

    video_path = os.path.join("Color", f'{case["case"]}.mp4')
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


def prepare_keys(case: dict, input_stream: str, output_stream: str) -> str:
    keys: str = case["ffmpeg_parameters"]
    keys = keys.replace("<input_stream>", input_stream)
    keys = keys.replace("<output_stream>", output_stream)
    return keys


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
        current_conf = set(system_pl) if not render_device else {system_pl, render_device}  # noqa: E501
        main_logger.info(f"Detected GPUs: {render_device}")
        main_logger.info(f"PC conf: {current_conf}")
        main_logger.info("Creating predefined errors json...")

        copy_test_cases(args)
        prepare_empty_reports(args, current_conf)
        exit(execute_tests(args, current_conf))
    except Exception as e:
        main_logger.error(f"Failed during script execution. Exception: {str(e)}")  # noqa: E501
        main_logger.error(f"Traceback: {traceback.format_exc()}")
        exit(-1)
