import json
import os
import platform
import time
import traceback
from copy import deepcopy
from process_results import fill_stream_info, compare_with_ma35, STREAM_INFO
from utils import (is_case_skipped, save_logs, save_results,
                   copy_test_cases, prepare_empty_reports)
from encoder import prepare_encoder_parameters, run_tool

from jobs_launcher.core.config import main_logger
from jobs_launcher.core.system_info import get_gpu


def execute_tests(args, current_conf):
    rc = 0
    test_cases_path = os.path.join(os.path.abspath(args.output), "test_cases.json")  # noqa: E501
    with open(test_cases_path, "r") as json_file:
        cases = json.load(json_file)

    logs_path = os.path.join(args.output, "tool_logs")
    if platform.system() == 'Windows':
        mediainfo = os.path.join(args.tool_path, "MediaInfo.exe")
    else:
        mediainfo = 'mediainfo'

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:
        # select tools to execute
        if "Encoder" in args.test_group:
            xma_tool_path = os.path.join(
                args.tool_path, 'xma', 'bin', 'ma35_encoder_app'
            )
            # clarify if we can install our binaries to a specific directory
            simple_tool_path = os.path.join(
                '/opt/amd/ama/amf_Release/bin', 'SimpleEncoderAMA'
            )

        output_path = os.path.join(args.output, "Color")
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        case_start_time = time.time()
        current_try = 0

        max_tries = args.retries

        while current_try < max_tries:
            main_logger.info(
                f"Start test case {case['case']}. Try: {current_try}"
            )
            error_messages = set()

            try:
                # prepare parameters/keys for simple tool and xma
                simple_log = os.path.join(
                    logs_path, f"{case['case']}_simple.log"
                )
                ma35_log = os.path.join(logs_path, f"{case['case']}_ma35.log")

                if "Encoder" in args.test_group:
                    prepared_keys, output_stream = prepare_encoder_parameters(
                        args, case, output_path=output_path,
                        simple_encoder=True
                    )

                case["script_info"].append(
                    f"Simple parameters: {prepared_keys}"
                )

                # main logic
                run_tool(simple_tool_path, prepared_keys, simple_log)

                execution_time = time.time() - case_start_time

                # results processing
                # get reference file
                if "Encoder" in args.test_group:
                    prepared_keys, reference_stream = prepare_encoder_parameters(  # noqa: E501
                        args, case, output_path=output_path,
                        simple_encoder=False
                    )

                run_tool(xma_tool_path, prepared_keys, ma35_log)

                output_stream_params = deepcopy(STREAM_INFO)
                reference_stream_params = deepcopy(STREAM_INFO)

                fill_stream_info(
                    mediainfo, output_stream, output_stream_params
                )

                fill_stream_info(
                    mediainfo, reference_stream, reference_stream_params
                )
                # fill_stream_quality(ffmpeg_vmaf_path, output_stream,
                #                     input_stream, output_stream_params)

                case["ref_stream_params"] = reference_stream_params
                case["output_stream_params"] = output_stream_params

                compare_with_ma35(
                    output_stream_params, reference_stream_params,
                    error_messages
                )

                save_logs(args, case, ma35_log)
                save_logs(args, case, simple_log)

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

                save_logs(args, case, ma35_log)
                save_logs(args, case, simple_log)

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
