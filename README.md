# galaxy-tool-test-workflow

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
planemo run test_tools.ga test_tools-job.yml --engine external_galaxy --galaxy_url https://usegalaxy.eu --galaxy_user_key <your_api_key> --test_output_xunit tests.xunit --simultaneous_uploads --no_early_termination
```

**Step 5:** Write test results as CSV:
```bash
python summarize_xunit_results.py tests.xunit --csv results
```
