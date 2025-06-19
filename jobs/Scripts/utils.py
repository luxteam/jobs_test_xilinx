import os
import traceback
import json
from datetime import datetime
from shutil import copyfile

from jobs_launcher.common.scripts.status_by_platform import get_status
from jobs_launcher.common.scripts.script_info_by_platform import get_script_info  # noqa: E501
from jobs_launcher.core.config import CASE_REPORT_SUFFIX, VIDEO_KEY, main_logger  # noqa: E501
from jobs_launcher.core.system_info import get_gpu


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])  # noqa: E501


def save_logs(args, case, log):
    try:
        if 'ma35' in log.lower():
            log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_ma35.html")  # noqa: E501
        else:
            log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + "_simple.html")  # noqa: E501

        with open(log, "r", encoding="utf-8") as file:
            lines = file.readlines()
        logs = "<!DOCTYPE html><html><body><span style=\"white-space: pre-line; font-family:'Courier New'\">\n"  # noqa: E501
        logs += "".join(lines)
        logs += "</span></body></html>"

        with open(log_destination_path, "w", encoding="utf-8") as file:
            file.write(logs)

        main_logger.info("Finish logs saving")

    except Exception as e:
        main_logger.error(f"Failed during logs saving. Exception: {str(e)}")
        main_logger.error(f"Traceback: {traceback.format_exc()}")


def select_extension(ma35_params: str) -> str:
    ma35_params = ma35_params.lower()
    if 'h264' in ma35_params:
        return 'h264'
    elif 'h265' in ma35_params or 'hevc' in ma35_params:
        return 'h265'
    elif 'av1' in ma35_params or 'vp9' in ma35_params:
        return 'ivf'


def prepare_keys(keys: str, input_stream: str, output_stream: str) -> str:
    keys = keys.replace("<input_stream>", input_stream)
    keys = keys.replace("<output_stream>", output_stream)
    return keys


def save_results(args, case, cases, execution_time=0.0, test_case_status="", error_messages=[]):  # noqa: E501
    case_report_path = os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX)  # noqa: E501
    with open(case_report_path, "r") as file:
        test_case_report = json.loads(file.read())[0]

    test_case_report["execution_time"] = execution_time
    test_case_report["ma35_log"] = os.path.join("tool_logs", case["case"] + "_ma35.html")  # noqa: E501
    test_case_report["simple_log"] = os.path.join("tool_logs", case["case"] + "_simple.html")  # noqa: E501

    test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")  # noqa: E501
    test_case_report["number_of_tries"] += 1

    test_case_report["message"] = (test_case_report["message"] + list(error_messages))  # noqa: E501

    test_case_report["simple_parameters"] = case["prepared_keys_simple"]
    test_case_report["xma_parameters"] = case["prepared_keys_xma"]
    test_case_report["ref_stream_params"] = case["ref_stream_params"]
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
