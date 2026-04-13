name: Check HTF Bias

on:
  workflow_dispatch:

jobs:
  check-bias:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install requests pandas numpy
      - name: Run bias check
        env:
          TWELVE_DATA_API_KEY: ${{ secrets.TWELVE_DATA_API_KEY }}
        run: python check_bias.py
