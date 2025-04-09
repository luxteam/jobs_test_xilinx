import argparse
import os
import sys

# set jobs_test_xilinx as a root dir for project
ROOT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
)
sys.path.append(ROOT_PATH)

from run_tests import run_tests  # noqa: E402


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--output", required=True, metavar="<dir>")
    parser.add_argument("--tool_path", required=True, metavar="<dir>")
    parser.add_argument("--retries", required=False, default=2, type=int)
    parser.add_argument("--test_group", required=True)
    parser.add_argument("--test_cases", required=True)

    return parser


args = createArgsParser().parse_args()
run_tests(args)
