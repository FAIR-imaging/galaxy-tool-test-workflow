# issue-34

**Step 1:** Obtain an up-to-date list of tools:
```bash
python tools.py
```

**Step 2:** Create a set of test TIFF images:
```bash
python create_test_data.py
```

**Step 4:** Run the Galaxy test workflow:
```bash
planemo run test_tools.ga test_tools-job.yml --engine external_galaxy --galaxy_url https://usegalaxy.eu --galaxy_user_key <your_api_key> --test_output_xunit test_xunit --simultaneous_uploads --no_early_termination
```

**Step 5:** Perform analysis of the workflow invocation:
1. Export the workflow invocation data as `Temporary Direct Download` and download.
2. Run the summarization script, where `target` is the file that you just downloaded:
   ```bash
   python summarize_test_results.py target
   ```
