# Complete Benchmark Runner
#cd /Users/shivamtiwari/Softwares/ExcelllmMsmes/llm_benchmarking
#python3 run_complete_benchmark.py
## Quick Start

Run the complete benchmark with a single command:

```bash
cd /Users/shivamtiwari/Softwares/ExcelllmMsmes/llm_benchmarking
python3 run_complete_benchmark.py
```

Or make it executable and run directly:

```bash
chmod +x run_complete_benchmark.py
./run_complete_benchmark.py
```

## What It Does

1. ✅ Checks all requirements (API keys, packages, files)
2. ✅ Runs benchmark on all enabled models
3. ✅ Shows real-time progress with:
   - Current model being tested
   - Question progress (X/Y)
   - Overall progress percentage
   - Estimated time remaining (ETA)
   - Score for each question
4. ✅ Generates all visualizations
5. ✅ Creates analysis reports
6. ✅ Shows final summary with top models

## Features

- **Progress Tracking**: See exactly how many questions are done and time remaining
- **Color-coded Scores**: Green (≥60%), Yellow (40-59%), Red (<40%)
- **Real-time Updates**: Progress bar updates as each question completes
- **Error Handling**: Continues even if individual questions fail
- **Complete Output**: All results saved to `results/` directory

## Output Locations

- **Metrics**: `results/metrics/`
- **Visualizations**: `results/visualizations/`
- **Logs**: `results/logs/`
- **Raw Responses**: `results/raw_responses/`

## Estimated Time

- Full benchmark (7 models × 30 questions): ~30-60 minutes
- Quick test (5 questions): ~5-10 minutes

## Troubleshooting

If you see errors:
1. Check `.env` file has valid API keys
2. Ensure all packages installed: `pip install -r requirements.txt`
3. Verify `question_generator/generated_questions.json` exists

