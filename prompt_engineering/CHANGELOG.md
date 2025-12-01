# Changelog - Prompt Engineering

## Latest Change: Use Baseline SQL Prompt

### Date: 2025-11-30

**Change**: Switched to using baseline SQL prompt instead of enhanced SQL prompt.

**Reason**: 
- Enhanced SQL prompt was causing degradation (-4.1% from baseline)
- Baseline SQL prompt already performs well (79.3% average)
- Keep enhanced prompts only for Methodology and Table Selection where they show improvements

**Implementation**:
- Updated `generate_enhanced_sql_prompt()` to use baseline prompt from `llm_benchmarking/prompts/sql_generation_prompt.txt`
- Kept enhanced prompts for methodology (+4.3% improvement) and table selection (+3.6% improvement)
- SQL now uses exact same prompt as baseline benchmark

**Expected Results**:
- SQL scores should match baseline (~79.3%)
- Overall score should improve due to methodology and table selection improvements
- More consistent performance across all components

**Files Modified**:
- `llama4_maverick_optimizer.py` - Updated SQL prompt generation to use baseline


