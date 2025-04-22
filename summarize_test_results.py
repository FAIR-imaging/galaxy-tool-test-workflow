#!/usr/bin/env python

import argparse
import json
import sys
import tarfile

import pandas as pd


parser = argparse.ArgumentParser()
parser.add_argument(
    'invocation',
    type=str,
    help='Export file of the invocation of the test workflow',
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

with tarfile.open(args.invocation) as tar:
    with tar.extractfile('collections_attrs.txt') as collections_file:
        collections = json.load(collections_file)
    with tar.extractfile('jobs_attrs.txt') as jobs_file:
        jobs = json.load(jobs_file)


def strip_prefix(s, prefix):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


filenames_by_id = dict()
for collection in collections:
    elements = collection['collection']['elements']
    for element in elements:
        filenames_by_id[element['encoded_id']] = strip_prefix(
            element['element_identifier'],
            prefix='data_images_tiff_',
        )


def find_dataset_ids(path, data):
    ids = list()
    if isinstance(data, dict):
        if 'id' in data:
            ids.append((path, data['id']))
        for key, value in data.items():
            ids.extend(find_dataset_ids(path + f'/{key}', value))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            ids.extend(find_dataset_ids(path + f'/{idx}', item))
    return ids


untested_tools = set(tool_ids)
tested_tools = dict()
for job in jobs:
    job_ok = (job['state'] == 'ok')
    tool_id = '/'.join(job['tool_id'].split('/')[3:5])
    inputs = {
        item[0].split('/')[1]: filenames_by_id.get(item[1])
        for item in find_dataset_ids('', job['params'])
        if item[1] is not None
    }
    if len(inputs) > 0 and tool_id != 'unzip/unzip':
        try:
            untested_tools.remove(tool_id)
        except KeyError:
            pass
        tested_tools.setdefault(tool_id, list())
        tested_tools[tool_id].append(
            dict(
                success=job_ok,
                inputs=inputs,
            ),
        )

report = dict(
    expectedly_tested_tools=list(
        frozenset(tested_tools.keys()) & frozenset(tool_ids)
    ),
    untested_tools=list(untested_tools),
    spuriously_tested_tools=list(
        frozenset(tested_tools.keys()) - frozenset(tool_ids)
    ),
    details=tested_tools,
)
json.dump(report, sys.stdout, indent=2)