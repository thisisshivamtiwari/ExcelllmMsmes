from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import os
import json
import csv
from pathlib import Path
import asyncio
from datetime import datetime
import shutil
import uuid
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ExcelLLM Data Generator API")

# CORS middleware - MUST be added BEFORE exception handlers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception at {request.url.path}: {str(exc)}")
    logger.error(traceback.format_exc())
    
    # Create response with CORS headers
    response = JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "Internal server error",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "path": str(request.url.path)
            }
        }
    )
    
    # Add CORS headers manually
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Paths - backend/main.py is in backend/, so parent.parent goes to project root
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADED_FILES_DIR = BASE_DIR / "uploaded_files"
UPLOADED_FILES_DIR.mkdir(exist_ok=True)

DATA_GENERATOR_DIR = BASE_DIR / "datagenerator"
DATA_GENERATOR_SCRIPT = DATA_GENERATOR_DIR / "data_generator.py"
GENERATED_DATA_DIR = DATA_GENERATOR_DIR / "generated_data"

QUESTION_GENERATOR_DIR = BASE_DIR / "question_generator"
QUESTION_GENERATOR_SCRIPT = QUESTION_GENERATOR_DIR / "question_generator.py"
QUESTIONS_FILE = QUESTION_GENERATOR_DIR / "generated_questions.json"
QUESTIONS_CSV_FILE = QUESTION_GENERATOR_DIR / "generated_questions.csv"

LLM_BENCHMARKING_DIR = BASE_DIR / "llm_benchmarking"
BENCHMARK_SCRIPT = LLM_BENCHMARKING_DIR / "run_complete_benchmark.py"
BENCHMARK_RESULTS_DIR = LLM_BENCHMARKING_DIR / "results"

PROMPT_ENGINEERING_DIR = BASE_DIR / "prompt_engineering"
PROMPT_TEST_SCRIPT = PROMPT_ENGINEERING_DIR / "test_enhanced_prompts.py"
PROMPT_RESULTS_DIR = PROMPT_ENGINEERING_DIR / "results"

COMPARISON_DIR = BASE_DIR / "enhanced_vs_baseline_vs_groundtruth"
COMPARISON_SCRIPT = COMPARISON_DIR / "comparison_analysis.py"
COMPARISON_RESULTS_DIR = COMPARISON_DIR / "results"


class GenerateRequest(BaseModel):
    production_rows: int = 200
    qc_rows: int = 150
    maintenance_rows: int = 50
    inventory_rows: int = 100
    no_continue: bool = False


class GenerateResponse(BaseModel):
    status: str
    message: str
    output: Optional[str] = None
    files: Optional[dict] = None
    error: Optional[str] = None


def test_python_packages(python_path):
    """Test if Python has required packages installed."""
    try:
        # Use a more reliable test - check each package individually
        test_script = """
import sys
try:
    import google.generativeai
    import pandas
    import dotenv
    sys.exit(0)
except ImportError as e:
    sys.exit(1)
"""
        result = subprocess.run(
            [python_path, "-c", test_script],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        # If timeout, assume it might work (packages might be slow to import)
        return True
    except Exception as e:
        # Log the error for debugging
        print(f"Error testing packages for {python_path}: {e}")
        return False


def find_python():
    """Find the correct Python interpreter with required packages."""
    python_paths = [
        "/opt/anaconda3/bin/python3",
        os.path.expanduser("~/anaconda3/bin/python3"),
        os.path.expanduser("~/miniconda3/bin/python3"),
    ]
    
    # First, try Anaconda/Miniconda Python (most likely to have packages)
    for python_path in python_paths:
        if os.path.exists(python_path):
            if test_python_packages(python_path):
                return python_path
            # Even if packages test fails, prefer Anaconda Python if it exists
            # (it likely has packages, test might just be slow)
            if "anaconda" in python_path.lower() or "miniconda" in python_path.lower():
                return python_path
    
    # Try system python3 with package check
    # Check both 'python3' and full paths
    python_candidates = ["python3", "python"]
    
    # Also check common system Python locations
    system_paths = [
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "/Library/Developer/CommandLineTools/usr/bin/python3",
    ]
    
    for python_cmd in python_candidates + system_paths:
        try:
            # Check if it's a full path and exists, or if it's a command
            if python_cmd in system_paths and not os.path.exists(python_cmd):
                continue
                
            result = subprocess.run(
                [python_cmd, "--version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                if test_python_packages(python_cmd):
                    return python_cmd
        except Exception:
            continue
    
    # Fallback: return Anaconda Python if exists, otherwise python3
    if os.path.exists("/opt/anaconda3/bin/python3"):
        return "/opt/anaconda3/bin/python3"
    
    return "python3"  # final fallback


@app.get("/")
async def root():
    return {"message": "ExcelLLM Data Generator API", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/files/test")
async def test_file_endpoints():
    """Test endpoint to verify file upload system is working."""
    try:
        # Test if modules are imported
        test_results = {
            "excel_loader": hasattr(excel_loader, 'load_file'),
            "file_validator": hasattr(file_validator, 'validate_file'),
            "metadata_extractor": hasattr(metadata_extractor, 'extract_metadata'),
            "uploaded_files_dir": str(UPLOADED_FILES_DIR),
            "uploaded_files_dir_exists": UPLOADED_FILES_DIR.exists(),
            "uploaded_files_dir_writable": os.access(UPLOADED_FILES_DIR, os.W_OK) if UPLOADED_FILES_DIR.exists() else False,
            "registry_count": len(uploaded_files_registry)
        }
        return {
            "status": "ok",
            "message": "File upload system is ready",
            "tests": test_results
        }
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
            "error_type": type(e).__name__
        }


@app.get("/api/python-status")
async def python_status():
    """Check Python environment and package availability."""
    try:
        python_path = find_python()
        
        if not python_path:
            return {
                "python_path": "not found",
                "python_version": "unknown",
                "has_required_packages": False,
                "status": "error",
                "message": "Python interpreter not found. Please install Python 3.",
            }
        
        has_packages = test_python_packages(python_path)
        
        # Get Python version
        python_version = "unknown"
        try:
            result = subprocess.run(
                [python_path, "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                version_output = result.stdout.decode("utf-8") or result.stderr.decode("utf-8")
                python_version = version_output.strip()
        except Exception as e:
            python_version = f"error: {str(e)}"
        
        # Get more detailed package info
        missing_packages = []
        if not has_packages:
            try:
                test_script = """
import sys
missing = []
try:
    import pandas
except ImportError:
    missing.append('pandas')
try:
    import google.generativeai
except ImportError:
    missing.append('google-generativeai')
try:
    import dotenv
except ImportError:
    missing.append('python-dotenv')
if missing:
    print(','.join(missing))
"""
                result = subprocess.run(
                    [python_path, "-c", test_script],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    missing_output = result.stdout.decode("utf-8").strip()
                    if missing_output and not missing_output.startswith("An error"):
                        missing_packages = [pkg.strip() for pkg in missing_output.split(",") if pkg.strip()]
            except Exception:
                pass
        
        message = "Python environment is ready"
        if not has_packages:
            if missing_packages:
                message = f"Missing packages: {', '.join(missing_packages)}. Install with: {python_path} -m pip install {' '.join(missing_packages)}"
            else:
                message = f"Missing required packages. Install with: {python_path} -m pip install pandas google-generativeai python-dotenv"
        
        return {
            "python_path": python_path,
            "python_version": python_version,
            "has_required_packages": has_packages,
            "missing_packages": missing_packages if missing_packages else [],
            "status": "ready" if has_packages else "missing_packages",
            "message": message,
        }
    except Exception as e:
        return {
            "python_path": "error",
            "python_version": "unknown",
            "has_required_packages": False,
            "status": "error",
            "message": f"Error checking Python status: {str(e)}",
        }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_data(request: GenerateRequest):
    """Trigger data generation with specified parameters."""
    try:
        python_path = find_python()
        
        # Verify Python has required packages before proceeding
        if not test_python_packages(python_path):
            error_msg = (
                f"Python at '{python_path}' does not have required packages installed.\n\n"
                f"Please install required packages:\n"
                f"  {python_path} -m pip install pandas google-generativeai python-dotenv\n\n"
                f"Or use Anaconda Python which likely has these packages:\n"
                f"  /opt/anaconda3/bin/python3"
            )
            return GenerateResponse(
                status="error",
                message="Missing required Python packages",
                output="",
                error=error_msg,
            )
        
        script_path = str(DATA_GENERATOR_SCRIPT)
        
        # Build command arguments
        cmd = [
            python_path,
            script_path,
            "--production-rows", str(request.production_rows),
            "--qc-rows", str(request.qc_rows),
            "--maintenance-rows", str(request.maintenance_rows),
            "--inventory-rows", str(request.inventory_rows),
        ]
        
        if request.no_continue:
            cmd.append("--no-continue")
        
        # Change to the datagenerator directory
        original_cwd = os.getcwd()
        os.chdir(str(DATA_GENERATOR_DIR))
        
        try:
            # Run the generator
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            output = stdout.decode("utf-8") if stdout else ""
            error_output = stderr.decode("utf-8") if stderr else ""
            
            if process.returncode != 0:
                # Provide helpful error message
                error_msg = error_output or output
                if "pandas" in error_msg.lower() or "google.generativeai" in error_msg.lower() or "dotenv" in error_msg.lower():
                    error_msg += (
                        f"\n\nTip: Install missing packages with:\n"
                        f"  {python_path} -m pip install pandas google-generativeai python-dotenv"
                    )
                
                return GenerateResponse(
                    status="error",
                    message="Data generation failed",
                    output=output,
                    error=error_msg,
                )
            
            # Check generated files
            files = {}
            file_names = [
                "production_logs.csv",
                "quality_control.csv",
                "maintenance_logs.csv",
                "inventory_logs.csv",
            ]
            
            for file_name in file_names:
                file_path = GENERATED_DATA_DIR / file_name
                if file_path.exists():
                    # Count rows (excluding header)
                    try:
                        with open(file_path, "r") as f:
                            lines = f.readlines()
                            row_count = len(lines) - 1 if len(lines) > 1 else 0
                            files[file_name] = row_count
                    except Exception:
                        files[file_name] = "unknown"
            
            return GenerateResponse(
                status="success",
                message="Data generation completed successfully",
                output=output,
                files=files,
            )
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        return GenerateResponse(
            status="error",
            message="Failed to execute data generator",
            error=str(e),
        )


@app.get("/api/files")
async def list_generated_files():
    """List all generated data files with their row counts."""
    files = {}
    
    if not GENERATED_DATA_DIR.exists():
        return {"files": {}, "message": "Generated data directory does not exist"}
    
    file_names = [
        "production_logs.csv",
        "quality_control.csv",
        "maintenance_logs.csv",
        "inventory_logs.csv",
    ]
    
    for file_name in file_names:
        file_path = GENERATED_DATA_DIR / file_name
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    row_count = len(lines) - 1 if len(lines) > 1 else 0
                    file_size = file_path.stat().st_size
                    files[file_name] = {
                        "rows": row_count,
                        "size_bytes": file_size,
                        "exists": True,
                    }
            except Exception as e:
                files[file_name] = {
                    "rows": 0,
                    "size_bytes": 0,
                    "exists": True,
                    "error": str(e),
                }
        else:
            files[file_name] = {"exists": False}
    
    return {"files": files}


@app.get("/api/data/{file_name}")
async def get_csv_data(
    file_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
):
    """Get CSV data with pagination and search."""
    allowed_files = [
        "production_logs.csv",
        "quality_control.csv",
        "maintenance_logs.csv",
        "inventory_logs.csv",
    ]
    
    if file_name not in allowed_files:
        raise HTTPException(status_code=400, detail=f"Invalid file name. Allowed: {', '.join(allowed_files)}")
    
    file_path = GENERATED_DATA_DIR / file_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            filtered_rows = []
            for row in rows:
                if any(search_lower in str(value).lower() for value in row.values()):
                    filtered_rows.append(row)
            rows = filtered_rows
        
        # Calculate pagination
        total_rows = len(rows)
        total_pages = (total_rows + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_rows = rows[start_idx:end_idx]
        
        # Get column names
        columns = list(paginated_rows[0].keys()) if paginated_rows else []
        
        return {
            "file_name": file_name,
            "columns": columns,
            "data": paginated_rows,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_rows": total_rows,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/api/data/{file_name}/stats")
async def get_file_stats(file_name: str):
    """Get statistics about a CSV file."""
    allowed_files = [
        "production_logs.csv",
        "quality_control.csv",
        "maintenance_logs.csv",
        "inventory_logs.csv",
    ]
    
    if file_name not in allowed_files:
        raise HTTPException(status_code=400, detail=f"Invalid file name")
    
    file_path = GENERATED_DATA_DIR / file_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return {
                "file_name": file_name,
                "total_rows": 0,
                "columns": [],
                "column_types": {},
            }
        
        columns = list(rows[0].keys())
        
        # Try to infer column types
        column_types = {}
        for col in columns:
            sample_values = [row[col] for row in rows[:100] if row[col]]
            if not sample_values:
                column_types[col] = "string"
                continue
            
            # Check if numeric
            numeric_count = sum(1 for v in sample_values if v.replace(".", "").replace("-", "").isdigit())
            if numeric_count > len(sample_values) * 0.8:
                column_types[col] = "number"
            # Check if date
            elif any(keyword in col.lower() for keyword in ["date", "time"]):
                column_types[col] = "date"
            else:
                column_types[col] = "string"
        
        return {
            "file_name": file_name,
            "total_rows": len(rows),
            "columns": columns,
            "column_types": column_types,
            "file_size_bytes": file_path.stat().st_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# ============================================================================
# Question Generator Endpoints
# ============================================================================

@app.post("/api/question-generator/generate")
async def generate_questions():
    """Generate questions from CSV data."""
    try:
        python_path = find_python()
        script_path = str(QUESTION_GENERATOR_SCRIPT)
        
        original_cwd = os.getcwd()
        os.chdir(str(QUESTION_GENERATOR_DIR))
        
        try:
            process = await asyncio.create_subprocess_exec(
                python_path,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""
            error_output = stderr.decode("utf-8") if stderr else ""
            
            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": "Question generation failed",
                    "output": output,
                    "error": error_output,
                }
            
            # Load generated questions
            questions_data = {}
            if QUESTIONS_FILE.exists():
                with open(QUESTIONS_FILE, "r") as f:
                    questions_data = json.load(f)
            
            return {
                "status": "success",
                "message": "Questions generated successfully",
                "output": output,
                "questions": questions_data,
            }
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate questions: {str(e)}",
            "error": str(e),
        }


@app.get("/api/question-generator/questions")
async def get_questions(category: Optional[str] = Query(None)):
    """Get generated questions, optionally filtered by category."""
    try:
        if not QUESTIONS_FILE.exists():
            return {
                "questions": {},
                "metadata": {},
                "message": f"No questions file found at {QUESTIONS_FILE}",
                "file_path": str(QUESTIONS_FILE),
                "file_exists": False,
            }
        
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if category:
            questions = data.get("questions", {}).get(category, [])
            return {"category": category, "questions": questions, "count": len(questions)}
        
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading questions: {str(e)}, Path: {QUESTIONS_FILE}",
        )


# ============================================================================
# LLM Benchmarking Endpoints
# ============================================================================

class BenchmarkRequest(BaseModel):
    sample_size: Optional[int] = None
    categories: Optional[List[str]] = None
    models: Optional[List[str]] = None
    use_gemini: bool = True


@app.post("/api/benchmark/run")
async def run_benchmark(request: BenchmarkRequest):
    """Run LLM benchmarking."""
    try:
        python_path = find_python()
        script_path = str(BENCHMARK_SCRIPT)
        
        cmd = [python_path, script_path]
        
        if request.sample_size:
            cmd.extend(["--sample", str(request.sample_size)])
        if request.categories:
            cmd.extend(["--categories"] + request.categories)
        if not request.use_gemini:
            cmd.append("--no-gemini")
        
        original_cwd = os.getcwd()
        os.chdir(str(LLM_BENCHMARKING_DIR))
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""
            error_output = stderr.decode("utf-8") if stderr else ""
            
            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": "Benchmark failed",
                    "output": output,
                    "error": error_output,
                }
            
            # Load results
            results_file = BENCHMARK_RESULTS_DIR / "metrics" / "all_results.json"
            results = {}
            if results_file.exists():
                with open(results_file, "r") as f:
                    results = json.load(f)
            
            return {
                "status": "success",
                "message": "Benchmark completed successfully",
                "output": output,
                "results": results,
            }
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run benchmark: {str(e)}",
            "error": str(e),
        }


@app.get("/api/benchmark/results")
async def get_benchmark_results():
    """Get benchmark results."""
    try:
        results_file = BENCHMARK_RESULTS_DIR / "metrics" / "all_results.json"
        if not results_file.exists():
            return {"results": {}, "message": "No benchmark results found"}
        
        with open(results_file, "r") as f:
            results = json.load(f)
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")


# ============================================================================
# Prompt Engineering Endpoints
# ============================================================================

@app.post("/api/prompt-engineering/test")
async def test_enhanced_prompts():
    """Test enhanced prompts."""
    try:
        python_path = find_python()
        script_path = str(PROMPT_TEST_SCRIPT)
        
        original_cwd = os.getcwd()
        os.chdir(str(PROMPT_ENGINEERING_DIR))
        
        try:
            process = await asyncio.create_subprocess_exec(
                python_path,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""
            error_output = stderr.decode("utf-8") if stderr else ""
            
            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": "Prompt testing failed",
                    "output": output,
                    "error": error_output,
                }
            
            # Load results
            results_file = PROMPT_RESULTS_DIR / "baseline_vs_enhanced_comparison.json"
            results = {}
            if results_file.exists():
                with open(results_file, "r") as f:
                    results = json.load(f)
            
            return {
                "status": "success",
                "message": "Prompt testing completed successfully",
                "output": output,
                "results": results,
            }
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to test prompts: {str(e)}",
            "error": str(e),
        }


@app.get("/api/prompt-engineering/results")
async def get_prompt_results():
    """Get prompt engineering results."""
    try:
        results_file = PROMPT_RESULTS_DIR / "baseline_vs_enhanced_comparison.json"
        if not results_file.exists():
            return {"results": {}, "message": "No prompt results found"}
        
        with open(results_file, "r") as f:
            results = json.load(f)
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")


# ============================================================================
# Comparison Analysis Endpoints
# ============================================================================

@app.post("/api/comparison/run")
async def run_comparison():
    """Run enhanced vs baseline vs ground truth comparison."""
    try:
        python_path = find_python()
        script_path = str(COMPARISON_SCRIPT)
        
        original_cwd = os.getcwd()
        os.chdir(str(COMPARISON_DIR))
        
        try:
            process = await asyncio.create_subprocess_exec(
                python_path,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8") if stdout else ""
            error_output = stderr.decode("utf-8") if stderr else ""
            
            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": "Comparison analysis failed",
                    "output": output,
                    "error": error_output,
                }
            
            # Load results
            results_file = COMPARISON_RESULTS_DIR / "three_way_comparison.json"
            results = {}
            if results_file.exists():
                with open(results_file, "r") as f:
                    results = json.load(f)
            
            return {
                "status": "success",
                "message": "Comparison analysis completed successfully",
                "output": output,
                "results": results,
            }
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run comparison: {str(e)}",
            "error": str(e),
        }


@app.get("/api/comparison/results")
async def get_comparison_results():
    """Get comparison analysis results."""
    try:
        results_file = COMPARISON_RESULTS_DIR / "three_way_comparison.json"
        if not results_file.exists():
            return {"results": {}, "message": "No comparison results found"}
        
        with open(results_file, "r") as f:
            results = json.load(f)
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")


# ============================================================================
# Visualization Image Endpoints
# ============================================================================
# IMPORTANT: List endpoints must come BEFORE parameterized routes
# Otherwise FastAPI will match /list as an image_name parameter

@app.get("/api/visualizations/test")
async def test_visualizations():
    """Test endpoint to verify visualization routes are working."""
    return {
        "status": "ok",
        "message": "Visualization endpoints are active",
        "benchmark_dir": str(BENCHMARK_RESULTS_DIR / "visualizations"),
        "benchmark_exists": (BENCHMARK_RESULTS_DIR / "visualizations").exists(),
        "prompt_dir": str(PROMPT_RESULTS_DIR / "visualizations"),
        "prompt_exists": (PROMPT_RESULTS_DIR / "visualizations").exists(),
        "comparison_dir": str(COMPARISON_RESULTS_DIR / "visualizations"),
        "comparison_exists": (COMPARISON_RESULTS_DIR / "visualizations").exists(),
    }


@app.get("/api/visualizations/benchmark/list")
async def list_benchmark_visualizations():
    """List available benchmark visualization images."""
    viz_dir = BENCHMARK_RESULTS_DIR / "visualizations"
    images = []
    if viz_dir.exists():
        for img_file in sorted(viz_dir.glob("*.png")):
            images.append({
                "name": img_file.stem.replace("_", " ").title(),
                "filename": img_file.name,
                "url": f"/api/visualizations/benchmark/{img_file.name}",
            })
    else:
        # Debug: return path info if directory doesn't exist
        return {
            "images": [],
            "debug": {
                "viz_dir": str(viz_dir),
                "exists": viz_dir.exists(),
                "benchmark_results_dir": str(BENCHMARK_RESULTS_DIR),
                "benchmark_results_exists": BENCHMARK_RESULTS_DIR.exists(),
            }
        }
    return {"images": images}


@app.get("/api/visualizations/prompt-engineering/list")
async def list_prompt_visualizations():
    """List available prompt engineering visualization images."""
    viz_dir = PROMPT_RESULTS_DIR / "visualizations"
    images = []
    if viz_dir.exists():
        for img_file in sorted(viz_dir.glob("*.png")):
            images.append({
                "name": img_file.stem.replace("_", " ").title(),
                "filename": img_file.name,
                "url": f"/api/visualizations/prompt-engineering/{img_file.name}",
            })
    else:
        # Debug: return path info if directory doesn't exist
        return {
            "images": [],
            "debug": {
                "viz_dir": str(viz_dir),
                "exists": viz_dir.exists(),
                "prompt_results_dir": str(PROMPT_RESULTS_DIR),
                "prompt_results_exists": PROMPT_RESULTS_DIR.exists(),
            }
        }
    return {"images": images}


@app.get("/api/visualizations/comparison/list")
async def list_comparison_visualizations():
    """List available comparison visualization images."""
    viz_dir = COMPARISON_RESULTS_DIR / "visualizations"
    images = []
    if viz_dir.exists():
        for img_file in sorted(viz_dir.glob("*.png")):
            images.append({
                "name": img_file.stem.replace("_", " ").title(),
                "filename": img_file.name,
                "url": f"/api/visualizations/comparison/{img_file.name}",
            })
    else:
        # Debug: return path info if directory doesn't exist
        return {
            "images": [],
            "debug": {
                "viz_dir": str(viz_dir),
                "exists": viz_dir.exists(),
                "comparison_results_dir": str(COMPARISON_RESULTS_DIR),
                "comparison_results_exists": COMPARISON_RESULTS_DIR.exists(),
            }
        }
    return {"images": images}


@app.get("/api/visualizations/benchmark/{image_name}")
async def get_benchmark_visualization(image_name: str):
    """Serve benchmark visualization images."""
    image_path = BENCHMARK_RESULTS_DIR / "visualizations" / image_name
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")


@app.get("/api/visualizations/prompt-engineering/{image_name}")
async def get_prompt_visualization(image_name: str):
    """Serve prompt engineering visualization images."""
    image_path = PROMPT_RESULTS_DIR / "visualizations" / image_name
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")


@app.get("/api/visualizations/comparison/{image_name}")
async def get_comparison_visualization(image_name: str):
    """Serve comparison visualization images."""
    image_path = COMPARISON_RESULTS_DIR / "visualizations" / image_name
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(image_path), media_type="image/png")


# ============================================================================
# Phase 1: Excel Parser API Endpoints
# ============================================================================

# Import Excel Parser modules
import sys
sys.path.insert(0, str(BASE_DIR))

from excel_parser.excel_loader import ExcelLoader
from excel_parser.file_validator import FileValidator
from excel_parser.metadata_extractor import MetadataExtractor

# Initialize parser components
excel_loader = ExcelLoader()
file_validator = FileValidator()
metadata_extractor = MetadataExtractor()

# Store file metadata in memory (in production, use database)
uploaded_files_registry: Dict[str, Dict[str, Any]] = {}


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel or CSV file.
    
    Returns:
        File ID and metadata
    """
    file_id = None
    saved_file_path = None
    
    try:
        # Validate filename exists
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        logger.info(f"Starting file upload: {file.filename}")
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.xlsx', '.xls', '.csv']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_ext}. Supported: .xlsx, .xls, .csv"
            )
        
        # Ensure uploaded_files directory exists
        UPLOADED_FILES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        saved_file_path = UPLOADED_FILES_DIR / f"{file_id}{file_ext}"
        
        try:
            # Read file content
            file_content = await file.read()
            
            # Check if file is empty
            if len(file_content) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty"
                )
            
            # Write file
            with open(saved_file_path, "wb") as buffer:
                buffer.write(file_content)
            
            logger.info(f"File saved: {saved_file_path} ({len(file_content)} bytes)")
            
        except IOError as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error saving file to disk: {str(e)}"
            )
        
        # Validate file
        try:
            validation_result = file_validator.validate_file(saved_file_path)
            if not validation_result['is_valid']:
                # Delete invalid file
                if saved_file_path.exists():
                    saved_file_path.unlink()
                logger.warning(f"File validation failed: {validation_result['errors']}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "File validation failed",
                        "errors": validation_result['errors'],
                        "warnings": validation_result['warnings']
                    }
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            if saved_file_path and saved_file_path.exists():
                saved_file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Error validating file: {str(e)}"
            )
        
        # Extract metadata
        try:
            logger.info(f"Extracting metadata for {file_id}...")
            metadata = metadata_extractor.extract_metadata(saved_file_path, include_sample=True)
            
            # Check if metadata extraction returned an error
            if isinstance(metadata, dict) and 'error' in metadata:
                logger.warning(f"Metadata extraction returned error: {metadata.get('error')}")
                # Continue with partial metadata
            else:
                logger.info(f"Metadata extracted successfully for {file_id}")
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            logger.error(traceback.format_exc())
            # Don't fail upload if metadata extraction fails, but log it
            metadata = {
                "error": f"Error extracting metadata: {str(e)}",
                "file_name": file.filename,
                "file_type": file_ext.replace('.', ''),
                "file_size_bytes": len(file_content) if 'file_content' in locals() else 0
            }
        
        # Store in registry
        file_info = {
            "file_id": file_id,
            "original_filename": file.filename,
            "saved_path": str(saved_file_path),
            "uploaded_at": datetime.now().isoformat(),
            "metadata": metadata,
            "validation": validation_result
        }
        uploaded_files_registry[file_id] = file_info
        
        logger.info(f"File upload successful: {file_id} ({file.filename})")
        
        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "metadata": metadata,
            "warnings": validation_result.get('warnings', [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Clean up file if it was created
        if saved_file_path and saved_file_path.exists():
            try:
                saved_file_path.unlink()
                logger.info(f"Cleaned up file: {saved_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file: {str(cleanup_error)}")
        
        error_detail = {
            "message": "Error uploading file",
            "error": str(e),
            "error_type": type(e).__name__,
            "file_id": file_id if file_id else None,
            "filename": file.filename if file and file.filename else None
        }
        
        # Include traceback in development (remove in production)
        import os
        if os.getenv("DEBUG", "false").lower() == "true":
            error_detail["traceback"] = traceback.format_exc()
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.get("/api/files/list")
async def list_uploaded_files():
    """List all uploaded files."""
    files = []
    for file_id, file_info in uploaded_files_registry.items():
        files.append({
            "file_id": file_id,
            "filename": file_info["original_filename"],
            "uploaded_at": file_info["uploaded_at"],
            "file_type": file_info["metadata"].get("file_type"),
            "row_count": file_info["metadata"].get("row_count") or file_info["metadata"].get("total_row_count", 0),
            "column_count": file_info["metadata"].get("column_count") or 0
        })
    
    return {
        "files": files,
        "total": len(files)
    }


@app.get("/api/files/{file_id}")
async def get_file_info(file_id: str):
    """Get detailed information about an uploaded file."""
    if file_id not in uploaded_files_registry:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = uploaded_files_registry[file_id]
    return {
        "file_id": file_id,
        "filename": file_info["original_filename"],
        "uploaded_at": file_info["uploaded_at"],
        "metadata": file_info["metadata"],
        "validation": file_info["validation"]
    }


@app.get("/api/files/{file_id}/metadata")
async def get_file_metadata(file_id: str):
    """Get metadata for an uploaded file."""
    if file_id not in uploaded_files_registry:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = uploaded_files_registry[file_id]
    return file_info["metadata"]


@app.post("/api/files/{file_id}/load")
async def load_file_data(file_id: str, sheet_name: Optional[str] = None):
    """Load the actual data from an uploaded file."""
    try:
        if file_id not in uploaded_files_registry:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = uploaded_files_registry[file_id]
        file_path = Path(file_info["saved_path"])
        
        # Check if file still exists
        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found on disk: {file_path.name}"
            )
        
        logger.info(f"Loading file data: {file_id} (sheet: {sheet_name})")
        
        # Load file
        result = excel_loader.load_file(file_path, sheet_name=sheet_name)
        
        if result['error']:
            logger.error(f"Error loading file {file_id}: {result['error']}")
            raise HTTPException(status_code=500, detail=result['error'])
        
        # Convert DataFrame(s) to JSON
        try:
            if isinstance(result['data'], dict):
                # Excel file with multiple sheets
                data = {
                    sheet: df.head(100).to_dict('records')  # Limit to first 100 rows for preview
                    for sheet, df in result['data'].items()
                }
            else:
                # CSV file
                data = result['data'].head(100).to_dict('records')  # Limit to first 100 rows
            
            logger.info(f"Successfully loaded data for file {file_id}")
            
            return {
                "file_id": file_id,
                "data": data,
                "metadata": result['metadata']
            }
        except Exception as e:
            logger.error(f"Error converting data to JSON for file {file_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file data: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error loading file: {str(e)}"
        )


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file."""
    if file_id not in uploaded_files_registry:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = uploaded_files_registry[file_id]
    file_path = Path(file_info["saved_path"])
    
    # Delete file
    if file_path.exists():
        file_path.unlink()
    
    # Remove from registry
    del uploaded_files_registry[file_id]
    
    return {
        "status": "success",
        "message": f"File {file_id} deleted successfully"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

