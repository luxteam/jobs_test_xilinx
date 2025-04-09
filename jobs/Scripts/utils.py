import os
import traceback

from jobs_launcher.core.config import main_logger


def is_case_skipped(case, render_platform):
    if case['status'] == 'skipped':
        return True

    return sum([render_platform & set(x) == set(x) for x in case.get('skip_on', '')])  # noqa: E501


def save_logs(args, case, ffmpeg_log):
    try:
        log_destination_path = os.path.join(args.output, "tool_logs", case["case"] + ".html")  # noqa: E501

        with open(ffmpeg_log, "r", encoding="utf-8") as file:
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
