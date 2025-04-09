import json
import os
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', required=True)
    args = parser.parse_args()
    work_dir = args.work_dir

    json_files = list(
        filter(
            lambda x: x.endswith('RPR.json'), os.listdir(work_dir)
        )
    )

    reports = []

    for file in json_files:
        json_content = json.load(open(os.path.join(work_dir, file), 'r'))[0]

        if json_content.get('group_timeout_exceeded', False):
            json_content['message'].append('Test group timeout exceeded')

        reports.append(json_content)
    with open(os.path.join(work_dir, 'report_compare.json'), 'w') as f: json.dump(reports, f, indent=4)
