#!/usr/bin/env python3
"""Debug SQL extraction issue"""

import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'llm_benchmarking'))
from evaluators.sql_comparator import SQLComparator

comparator = SQLComparator()

# Load actual response
results_file = Path(__file__).parent / 'results' / 'enhanced_prompt_results.json'
with open(results_file, 'r') as f:
    data = json.load(f)

first_result = data['results'][0]
sql_raw = first_result['response'].get('sql', '')

print('SQL Raw Response Length:', len(sql_raw))
print('First 300 chars:')
print(sql_raw[:300])
print()

# Test SQLComparator extraction
extracted = comparator.extract_sql_from_response(sql_raw)
print('SQLComparator extracted length:', len(extracted))
if extracted:
    print('Extracted (first 200 chars):')
    print(extracted[:200])
else:
    print('SQLComparator extraction FAILED')
    print()
    
    # Try manual regex
    print('Trying manual regex...')
    pattern = r'```sql\s*(.*?)\s*```'
    match = re.search(pattern, sql_raw, re.DOTALL | re.IGNORECASE)
    if match:
        manual_extracted = match.group(1).strip()
        print('Manual regex SUCCESS!')
        print('Length:', len(manual_extracted))
        print('First 200 chars:', manual_extracted[:200])
    else:
        print('Manual regex also failed')
        # Try simple string find
        if '```sql' in sql_raw:
            print('Found ```sql in string')
            start = sql_raw.find('```sql') + 6
            end = sql_raw.find('```', start)
            if end > start:
                simple_extracted = sql_raw[start:end].strip()
                print('Simple extraction SUCCESS!')
                print('Length:', len(simple_extracted))
                print('First 200 chars:', simple_extracted[:200])

