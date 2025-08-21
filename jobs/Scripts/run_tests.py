import json
import os
import platform
import time
import traceback

from decoder import prepare_decoder_input, prepare_decoder_parameters
from encoder import prepare_encoder_parameters, run_tool
from exceptions import ToolFailedException
from ffmpeg import prepare_ffmpeg_parameters, measure_ffmpeg_performance
from process_results import get_ffprobe_info, hash_and_comapre
from scaler import prepare_scaler_parameters
from transcoder import prepare_transcoder_input, prepare_transcoder_parameters
from utils import (copy_test_cases, is_case_skipped, prepare_empty_reports,
                   save_logs, save_results, remove_artifact)

from jobs_launcher.core.config import main_logger
from jobs_launcher.core.system_info import get_gpu


def execute_tests(args, current_conf):
    rc = 0
    test_cases_path = os.path.join(os.path.abspath(args.output), "test_cases.json")  # noqa: E501
    with open(test_cases_path, "r") as json_file:
        cases = json.load(json_file)

    logs_path = os.path.join(args.output, "tool_logs")
    # keep for ffmpeg testing
    # if platform.system() == 'Windows':
    #     mediainfo = os.path.join(args.tool_path, "MediaInfo.exe")
    # else:
    #     mediainfo = 'mediainfo'

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:
        # select tools to execute
        binaries_common_path = '/opt/amd/ama/'
        if args.tools == "SimpleSamples":
            if "Encoder" in args.test_group:
                xma_tool_path = os.path.join(
                    binaries_common_path, 'ma35', 'bin', 'ma35_encoder_app'
                )
                simple_tool_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA'
                )
            elif "Decoder" in args.test_group:
                xma_tool_path = os.path.join(
                    binaries_common_path, 'ma35', 'bin', 'ma35_decoder_app'
                )
                simple_tool_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin', 'SimpleDecoderAMA'
                )
                encoder_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA'
                )
            elif "Scaler" in args.test_group:
                xma_tool_path = os.path.join(
                    binaries_common_path, 'ma35', 'bin', 'ma35_scaler_app'
                )
                simple_tool_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin', 'SimpleScalerAMA'
                )
            elif "Transcoder" in args.test_group:
                xma_tool_path = os.path.join(
                    binaries_common_path, 'ma35', 'bin', 'ma35_transcoder_app'
                )
                simple_tool_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin',
                    'SimpleTranscoderAMA'
                )
                encoder_path = os.path.join(
                    binaries_common_path, 'amf_Release', 'bin', 'SimpleEncoderAMA'
                )
        elif args.tools == "FFMPEG":
            amf_ffmpeg_path = os.path.join(
                binaries_common_path, 'amf_Release', 'bin', 'ffmpeg'
            )
            xma_ffmpeg_path = os.path.join(
                binaries_common_path, 'ma35', 'bin', 'ffmpeg'
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
                if args.tools == "SimpleSamples":
                    # prepare parameters/keys for simple tool and xma
                    simple_log = os.path.join(
                        logs_path, f"{case['case']}_simple.log"
                    )
                    ma35_log = os.path.join(logs_path, f"{case['case']}_ma35.log")
                    input_preparation_log = os.path.join(logs_path, f"{case['case']}_input_preparation.log")  # noqa: E501

                    if "Encoder" in args.test_group:
                        prepared_keys, input_stream, output_stream = prepare_encoder_parameters(
                            case, output_path=output_path,
                            simple_encoder=True
                        )
                        ma35_prepared_keys, input_stream, reference_stream = prepare_encoder_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_encoder=False
                        )
                    elif "Decoder" in args.test_group:
                        # prepare output file and keys
                        prepared_keys, input_stream, output_stream = prepare_decoder_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_decoder=True
                        )
                        ma35_prepared_keys, input_stream, reference_stream = prepare_decoder_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_decoder=False
                        )

                        # prepare input file for decoder
                        prepare_decoder_input(
                            case, encoder_path, input_stream,
                            input_preparation_log
                        )
                    elif "Scaler" in args.test_group:
                        prepared_keys, input_stream, output_stream = prepare_scaler_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_scaler=True
                        )
                        ma35_prepared_keys, input_stream, reference_stream = prepare_scaler_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_scaler=False
                        )
                    elif "Transcoder" in args.test_group:
                        prepared_keys, input_stream, output_stream = prepare_transcoder_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_transcoder=True
                        )
                        ma35_prepared_keys, input_stream, reference_stream = prepare_transcoder_parameters(  # noqa: E501
                            case, output_path=output_path,
                            simple_transcoder=False
                        )
                        # prepare input file for transcoder
                        prepare_transcoder_input(
                            case, encoder_path, input_stream,
                            input_preparation_log
                        )

                    case["script_info"].append(
                        f"Simple parameters: {prepared_keys}"
                    )
                    case["script_info"].append(
                        f"MA35 parameters: {ma35_prepared_keys}"
                    )

                    # main logic
                    run_tool(simple_tool_path, prepared_keys, simple_log)
                    run_tool(xma_tool_path, ma35_prepared_keys, ma35_log)

                    execution_time = time.time() - case_start_time

                    # results processing
                    reference_stream_params = {}
                    output_stream_params = {}

                    if "Scaler" not in args.test_group:
                        compare_result = hash_and_comapre(output_stream, reference_stream)  # noqa: E501

                        if compare_result == 'identical':
                            test_case_status = "passed"
                        else:
                            test_case_status = "failed"
                            output_stream_params = get_ffprobe_info(case, output_stream)  # noqa: E501
                            reference_stream_params = get_ffprobe_info(
                                case, reference_stream
                            )

                        # remove artifacts as they may be too heavy
                        remove_artifact(output_stream)
                        remove_artifact(reference_stream)
                        remove_artifact(input_stream)
                    else:
                        output_stream_params = []
                        reference_stream_params = []

                        output_dir = os.path.split(output_stream)[0]
                        output_filename = os.path.split(output_stream)[1]
                        output_files = os.listdir(output_dir)
                        ma35_res = []
                        simple_res = []

                        for name in output_files:
                            if '_ma35' in name and f'{output_filename}_' in name:
                                ma35_res.append(name)
                            if '_ma35' not in name and f'{output_filename}_' in name:  # noqa: E501
                                simple_res.append(name)

                        ma35_res.sort()
                        simple_res.sort()

                        for index, value in enumerate(simple_res):
                            output_stream = os.path.join(output_dir, value)
                            reference_stream = os.path.join(output_dir, ma35_res[index])  # noqa: E501

                            compare_result = hash_and_comapre(output_stream, reference_stream)  # noqa: E501

                            if compare_result != 'identical':
                                output_info = get_ffprobe_info(case, output_stream)
                                reference_info = get_ffprobe_info(case, reference_stream)  # noqa: E501

                                output_stream_params.append(output_info)
                                reference_stream_params.append(reference_info)  # noqa: E501

                            # remove artifacts as they may be too heavy
                            remove_artifact(output_stream)
                            remove_artifact(reference_stream)
                            remove_artifact(input_stream)

                        if output_stream_params == []:
                            test_case_status = "passed"
                        else:
                            test_case_status = "failed"

                    case["ref_stream_params"] = reference_stream_params
                    case["output_stream_params"] = output_stream_params

                    save_logs(args, case, ma35_log)
                    save_logs(args, case, simple_log)

                    if os.path.exists(input_preparation_log):
                        save_logs(args, case, input_preparation_log)
                elif args.tools == "FFMPEG":
                    amf_log = os.path.join(
                        logs_path, f"{case['case']}_amf.log"
                    )
                    ma35_log = os.path.join(logs_path, f"{case['case']}_ma35.log")

                    prepared_keys, input_stream, output_stream = prepare_ffmpeg_parameters(
                        case, input_path=args.tool_path, output_path=output_path, amf_ffmpeg=True
                    )
                    xma_prepared_keys, input_stream, output_stream = prepare_ffmpeg_parameters(
                        case, input_path=args.tool_path, output_path=output_path, amf_ffmpeg=False
                    )

                    case["script_info"].append(
                        f"Simple parameters: {prepared_keys}"
                    )
                    case["script_info"].append(
                        f"MA35 parameters: {ma35_prepared_keys}"
                    )

                    # main logic
                    run_tool(amf_ffmpeg_path, prepared_keys, amf_log)
                    run_tool(xma_ffmpeg_path, xma_prepared_keys, ma35_log)
                    execution_time = time.time() - case_start_time

                    # results processing
                    reference_stream_params = {}
                    output_stream_params = {}

                    # compare hashes
                    compare_result = hash_and_comapre(output_stream, reference_stream)  # noqa: E501

                    if compare_result == 'identical':
                        test_case_status = "passed"
                    else:
                        test_case_status = "failed"
                        output_stream_params = get_ffprobe_info(case, output_stream)  # noqa: E501
                        reference_stream_params = get_ffprobe_info(
                            case, reference_stream
                        )

                    case["ref_stream_params"] = reference_stream_params
                    case["output_stream_params"] = output_stream_params

                    # measure preformance
                    measure_ffmpeg_performance(amf_log, ma35_log, error_messages=error_messages)

                    save_logs(args, case, ma35_log)
                    save_logs(args, case, amf_log)

                save_results(args, case, cases,
                             execution_time=execution_time,
                             test_case_status=test_case_status,
                             error_messages=error_messages)
                break
            except Exception as e:
                execution_time = time.time() - case_start_time

                save_logs(args, case, ma35_log)
                save_logs(args, case, simple_log)

                if os.path.exists(input_preparation_log):
                    save_logs(args, case, input_preparation_log)

                test_case_status = "error"
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
