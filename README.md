# issue-34

**Step 1:** Obtain an up-to-date list of tools:
```bash
python tools.py
```

**Step 2:** Create a set of test TIFF images:
```bash
python create_test_data.py
```

**Step 3:** Run the Galaxy test workflow:
1. Upload `data/images.zip` into Galaxy.
2. Run the `Unzip` tool and unzip all files.
3. Create workflow where a dataset collection is connected to each tool to be tested.
4. Run the workflow with the unzipped collection.

**Step 4:** Perform analysis of the workflow invocation:
1. Export the workflow invocation data as `Temporary Direct Download` and download.
2. Run the summarization script, where `target` is the file that you just downloaded:
   ```bash
   python summarize_test_results.py target
   ```