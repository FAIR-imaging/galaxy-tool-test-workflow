#!/usr/bin/env python

import argparse
import json
import re
import sys
from xml.etree import ElementTree

import pandas as pd


parser = argparse.ArgumentParser()
parser.add_argument(
    'xunit',
    type=str,
    help='XUnit XML file produced by the workflow run.',
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

        tested_tools[tool_id] = dict()
        tested_tool = tested_tools[tool_id]
        tested_tool['inputs'] = {
            input_name: filenames_by_ids[input_data['id']]
            for input_name, input_data in job['inputs'].items()
            if input_data['id'] in filenames_by_ids
        }
        tested_tool['success'] = (job['state'] == 'ok')

report = dict(
    expectedly_tested_tools=list(
        frozenset(tested_tools.keys()) & frozenset(tool_ids)
    ),
    untested_tools=list(
        frozenset(tool_ids) - frozenset(tested_tools.keys())
    ),
    spuriously_tested_tools=list(
        frozenset(tested_tools.keys()) - frozenset(tool_ids)
    ),
    results=tested_tools,
)
json.dump(report, sys.stdout, indent=2)