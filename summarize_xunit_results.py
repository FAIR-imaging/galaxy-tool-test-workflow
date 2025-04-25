#!/usr/bin/env python

import argparse
import json
import pathlib
import re
import sys
from xml.etree import ElementTree

import numpy as np
import pandas as pd


parser = argparse.ArgumentParser()
parser.add_argument(
    'xunit',
    type=str,
    help='XUnit XML file produced by the workflow run.',
)
parser.add_argument(
    '--csv',
    type=str,
    default=None,
    help='Directory where results should be written as CSV.',
)
args = parser.parse_args()

tools_df = pd.read_csv('data/tools.csv')
tool_ids = list()
for ridx, row in tools_df.iterrows():
    suite_id = row['Suite ID']
    tool_ids_chunk_str = row['Tool IDs']
    tool_ids_chunk = json.loads(tool_ids_chunk_str.replace("'", '"'))
    tool_ids_chunk = [
        f'{suite_id}/{tool_id}' for tool_id in tool_ids_chunk
    ]
    tool_ids.extend(tool_ids_chunk)

tree = ElementTree.parse(args.xunit)
testcase = tree.getroot()[0]
error = testcase.find('error')

if error is None:
    print('All tests passed.')
    sys.exit(0)

steps = json.loads(error.text)['invocation_details']['steps']


def find_tool(data, tool_id):
    if isinstance(data, dict):
        if 'tool_id' in data.keys() and tool_id in data['tool_id']:
            yield data
        else:
            for subdata in data.values():
                yield from find_tool(subdata, tool_id)
    elif isinstance(data, list):
        for item in data:
            yield from find_tool(item, tool_id)
    else:
        return None


unzip_output_filename_pattern = re.compile(r'^.+\|data_images_tiff_(.+)__$')

filenames_by_ids = dict()
for unzip_tool in find_tool(steps, 'unzip/unzip'):
    for key, output_data in unzip_tool['outputs'].items():
        key_match = unzip_output_filename_pattern.match(key)
        filename = key_match.group(1)
        filenames_by_ids[output_data['id']] = filename

tested_tools = dict()
for step in steps.values():
    for job in step.get('jobs', list()):

        if 'tool_id' not in job:
            continue

        tool_id = '/'.join(job['tool_id'].split('/')[3:5])
        if tool_id == 'unzip/unzip':
            continue

        tool_test_results = tested_tools.setdefault(tool_id, list())
        tool_test_result = dict()
        tool_test_results.append(tool_test_result)
        tool_test_result['inputs'] = {
            input_name: filenames_by_ids[input_data['id']]
            for input_name, input_data in job['inputs'].items()
            if input_data['id'] in filenames_by_ids
        }
        tool_test_result['state'] = job['state']  # `ok` means success

report = dict(
    tested_tools=sorted(
        frozenset(tested_tools.keys())
    ),
    untested_tools=sorted(
        frozenset(tool_ids) - frozenset(tested_tools.keys())
    ),
    spuriously_tested_tools=sorted(
        frozenset(tested_tools.keys()) - frozenset(tool_ids)
    ),
    results=tested_tools,
)

if args.csv is None:
    json.dump(report, sys.stdout, indent=2)

else:
    csv_path = pathlib.Path(args.csv)
    csv_path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame.from_dict(
        {
            'Tested Tools': pd.Series(
                report['tested_tools']
            ),
            'Success Rate': pd.Series(
                [
                    np.mean(
                        [test['state'] == 'ok' for test in report['results'][tool_id]]
                    )
                    for tool_id in report['tested_tools']
                ]
            ),
            '': pd.Series([]),
            'Untested Tools': pd.Series(report['untested_tools']),
            'Spuriously Tested Tools': pd.Series(
                report['spuriously_tested_tools']
            ),
        }
    )
    df.to_csv(csv_path / 'overview.csv', index=False)

    for tool_id, tool_test_results in report['results'].items():

        inputs = set()
        for tool_test_result in tool_test_results:
            inputs |= frozenset(tool_test_result['inputs'].keys())
        inputs = sorted(inputs)

        tool_test_results_df = pd.DataFrame.from_dict(
            {
                f'Inputs/{input_name}': pd.Series(
                    [
                        tool_test_result['inputs'][input_name]
                        for tool_test_result in tool_test_results
                    ]
                )
                for input_name in inputs
            } | {
                'State': pd.Series(
                    [test['state'] for test in tool_test_results]
                ),
            } | {
                'Success': pd.Series(
                    [test['state'] == 'ok' for test in tool_test_results]
                ),
            }
        )
        tool_test_results_filepath = csv_path / f'{tool_id}.csv'
        tool_test_results_filepath.parent.mkdir(
            parents=True, exist_ok=True
        )
        tool_test_results_df.to_csv(
            tool_test_results_filepath, index=False
        )
