import json
import pathlib

import wget
import pandas as pd


data_dir_path = pathlib.Path('data')
data_dir_path.mkdir(parents=True, exist_ok=True)


def get_tools(cached: bool = True):
    tools_json_filename = data_dir_path / 'tools.json'
    if not cached or not tools_json_filename.exists():
        wget.download('https://raw.githubusercontent.com/galaxyproject/galaxy_codex/refs/heads/main/communities/imaging/resources/tools_filtered_by_ts_categories.json', out=str(tools_json_filename))

    with open(tools_json_filename, 'r') as tools_json_file:
        tools = json.load(tools_json_file)

    tools_df = pd.DataFrame(tools)
    tools_df.to_csv(str(data_dir_path / 'tools.csv'), index=False)


if __name__ == '__main__':
    get_tools()