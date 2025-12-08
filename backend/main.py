from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request, Depends, status
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
import gc
from dotenv import load_dotenv

# Multi-Tenant SaaS imports (after logger is defined)
MONGODB_AVAILABLE = False
try:
    from backend.database import connect_to_mongodb, close_mongodb_connection
    from backend.models.user import UserCreate, UserLogin, UserResponse, UserInDB
    from backend.models.industry import IndustryResponse
    from backend.services.auth_service import create_user, authenticate_user, create_access_token, get_user_by_id
    from backend.services.industry_service import seed_industries, get_all_industries, get_industry_by_name
    from backend.middleware.auth_middleware import get_current_user
    MONGODB_AVAILABLE = True
except ImportError as e:
    # Logger might not be defined yet, use print for initial warning
    import sys
    print(f"Warning: MongoDB/Auth modules not available: {str(e)}", file=sys.stderr)

# Load environment variables from .env file
# Try backend/.env first, then project root .env
BACKEND_ENV = Path(__file__).resolve().parent / ".env"
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_ENV = BASE_DIR / ".env"

if BACKEND_ENV.exists():
    load_dotenv(BACKEND_ENV)
elif ROOT_ENV.exists():
    load_dotenv(ROOT_ENV)
else:
    # Try loading from current directory as fallback
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log that environment variables were loaded
if BACKEND_ENV.exists():
    logger.info(f"Loaded environment variables from {BACKEND_ENV}")
elif ROOT_ENV.exists():
    logger.info(f"Loaded environment variables from {ROOT_ENV}")
else:
    logger.info("Environment variables loaded from system/default location")

# Multi-Tenant SaaS imports (after logger is defined)
# Add backend directory to path for imports
import sys
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

MONGODB_AVAILABLE = False
try:
    from database import connect_to_mongodb, close_mongodb_connection
    from models.user import UserCreate, UserLogin, UserResponse, UserInDB
    from models.industry import IndustryResponse
    from services.auth_service import create_user, authenticate_user, create_access_token, get_user_by_id
    from services.industry_service import seed_industries, get_all_industries, get_industry_by_name
    from middleware.auth_middleware import get_current_user
    MONGODB_AVAILABLE = True
    logger.info("✅ Multi-tenant SaaS modules loaded successfully")
except ImportError as e:
    logger.warning(f"MongoDB/Auth modules not available: {str(e)}")
    import traceback
    logger.debug(traceback.format_exc())

app = FastAPI(title="ExcelLLM Data Generator API")

# MongoDB startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB connection on startup"""
    if MONGODB_AVAILABLE:
        try:
            await connect_to_mongodb()
            # Seed industries on startup
            await seed_industries()
            logger.info("✅ MongoDB initialized and industries seeded")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MongoDB: {e}")
            logger.warning("Continuing without MongoDB (some features may not work)")

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    if MONGODB_AVAILABLE:
        try:
            await close_mongodb_connection()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")

# CORS middleware - MUST be added BEFORE exception handlers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Exception handler for HTTPException (to ensure CORS headers)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    return response

# Exception handler for RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
    return response

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {str(exc)}")
    logger.error(traceback.format_exc())
    
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
    return response

# Paths - backend/main.py is in backend/, so parent.parent goes to project root
# BASE_DIR is already defined above for loading .env file
UPLOADED_FILES_DIR = BASE_DIR / "uploaded_files"
UPLOADED_FILES_DIR.mkdir(exist_ok=True)

# Phase 3: Semantic Indexing imports (after BASE_DIR is defined)
import sys
sys.path.insert(0, str(BASE_DIR))  # Add project root to path for embeddings module
try:
    from embeddings import Embedder, VectorStore, Retriever
    EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Embeddings module not available: {str(e)}")
    EMBEDDINGS_AVAILABLE = False
    Embedder = None
    VectorStore = None
    Retriever = None

# Phase 4: LangChain Agent System imports
try:
    from tools import ExcelRetriever, DataCalculator, TrendAnalyzer, ComparativeAnalyzer, KPICalculator, GraphGenerator
    from agent import ExcelAgent
    from agent.tool_wrapper import (
        create_excel_retriever_tool,
        create_data_calculator_tool,
        create_trend_analyzer_tool,
        create_comparative_analyzer_tool,
        create_kpi_calculator_tool,
        create_graph_generator_tool
    )
    AGENT_AVAILABLE = True
    
    # Check if prompt_engineering is available
    try:
        from prompt_engineering.llama4_maverick_optimizer import EnhancedPromptEngineer
        PROMPT_ENGINEERING_AVAILABLE = True
        logger.info("✓ Prompt engineering module available")
    except ImportError as e:
        PROMPT_ENGINEERING_AVAILABLE = False
        logger.warning(f"Prompt engineering module not available: {e}")
except ImportError as e:
    logger.warning(f"Agent module not available: {str(e)}")
    AGENT_AVAILABLE = False
    PROMPT_ENGINEERING_AVAILABLE = False

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


# ============================================================================
# MULTI-TENANT SAAS: Authentication & User Management
# ============================================================================

if MONGODB_AVAILABLE:
    @app.post("/api/auth/signup", response_model=Dict[str, Any])
    async def signup(user_data: UserCreate):
        """Create a new user account"""
        try:
            # Validate industry exists
            industry = await get_industry_by_name(user_data.industry)
            if not industry:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid industry: {user_data.industry}"
                )
            
            # Create user
            user = await create_user(user_data)
            
            # Create access token
            access_token = create_access_token(data={"sub": user.id})
            
            return {
                "success": True,
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "industry": user.industry,
                    "name": user.profile.name if user.profile else None,
                    "company": user.profile.company if user.profile else None
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/auth/login", response_model=Dict[str, Any])
    async def login(credentials: UserLogin):
        """Login and get access token"""
        try:
            # Authenticate user
            user = await authenticate_user(credentials.email, credentials.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create access token
            access_token = create_access_token(data={"sub": str(user.id)})
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "industry": user.industry,
                    "name": user.profile.name if user.profile else None,
                    "company": user.profile.company if user.profile else None
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/auth/me", response_model=Dict[str, Any])
    async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
        """Get current authenticated user information"""
        return {
            "success": True,
            "user": {
                "id": str(current_user.id),
                    "email": current_user.email,
                    "industry": current_user.industry,
                    "created_at": current_user.created_at.isoformat(),
                    "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
                    "profile": {
                        "name": current_user.profile.name if current_user.profile else None,
                        "company": current_user.profile.company if current_user.profile else None
                    } if current_user.profile else None
                }
            }


    # ============================================================================
    # MULTI-TENANT SAAS: Industry Management
    # ============================================================================

    @app.get("/api/industries", response_model=List[Dict[str, Any]])
    async def get_industries():
        """Get all available industries"""
        try:
            industries = await get_all_industries()
            return [
                {
                    "id": ind.id,
                    "name": ind.name,
                    "display_name": ind.display_name,
                    "description": ind.description,
                    "icon": ind.icon,
                    "schema_templates": ind.schema_templates
                }
                for ind in industries
            ]
        except Exception as e:
            logger.error(f"Error getting industries: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/industries/{industry_name}", response_model=Dict[str, Any])
    async def get_industry(industry_name: str):
        """Get industry by name"""
        try:
            industry = await get_industry_by_name(industry_name)
            if not industry:
                raise HTTPException(status_code=404, detail="Industry not found")
            
            return {
                "id": industry.id,
                "name": industry.name,
                "display_name": industry.display_name,
                "description": industry.description,
                "icon": industry.icon,
                "schema_templates": industry.schema_templates
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting industry: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


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
from excel_parser.schema_detector import SchemaDetector
from excel_parser.gemini_schema_analyzer import GeminiSchemaAnalyzer

# Initialize parser components
excel_loader = ExcelLoader()
file_validator = FileValidator()
metadata_extractor = MetadataExtractor()

# Initialize schema detector with Gemini support
gemini_api_key = os.getenv('GEMINI_API_KEY')
# Initialize Gemini analyzer, but don't fail if it doesn't work
gemini_analyzer = None
if gemini_api_key:
    try:
        gemini_analyzer = GeminiSchemaAnalyzer(gemini_api_key)
        logger.info("✓ Gemini Schema Analyzer initialized successfully")
    except Exception as e:
        logger.warning(f"⚠ Gemini Schema Analyzer initialization failed (non-critical): {str(e)}")
        logger.warning("   Schema analysis will continue without Gemini enhancements")
        gemini_analyzer = None
schema_detector = SchemaDetector(
    use_gemini=gemini_api_key is not None,
    gemini_api_key=gemini_api_key
)

# Log Gemini status
if gemini_api_key:
    masked_key = f"{'*' * (len(gemini_api_key) - 8)}{gemini_api_key[-8:]}" if len(gemini_api_key) > 8 else "***"
    logger.info(f"Gemini API key found: {masked_key}")
    if gemini_analyzer and gemini_analyzer.enabled:
        logger.info("✓ Gemini API initialized and ready for semantic analysis")
    else:
        logger.warning("⚠ Gemini API key provided but initialization failed - check google-generativeai package")
else:
    logger.info("ℹ Gemini API key not found - semantic analysis will be limited to statistical methods")

# Store file metadata in memory (will be persisted to JSON files)
uploaded_files_registry: Dict[str, Dict[str, Any]] = {}

# Metadata directory
METADATA_DIR = UPLOADED_FILES_DIR / "metadata"
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# Phase 3: Semantic Indexing setup
VECTOR_STORE_DIR = BASE_DIR / "vectorstore"
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Initialize embeddings components (lazy initialization)
_embedder = None
_vector_store = None
_retriever = None

def get_embedder():
    """Get or create embedder instance."""
    global _embedder
    if not EMBEDDINGS_AVAILABLE:
        return None
    if _embedder is None:
        try:
            _embedder = Embedder()
            logger.info("✓ Embedder initialized")
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {str(e)}")
            _embedder = None
    return _embedder

def get_vector_store():
    """Get or create vector store instance."""
    global _vector_store
    if not EMBEDDINGS_AVAILABLE:
        return None
    if _vector_store is None:
        try:
            _vector_store = VectorStore(persist_directory=VECTOR_STORE_DIR)
            logger.info("✓ Vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            _vector_store = None
    return _vector_store

def get_retriever():
    """Get or create retriever instance."""
    global _retriever
    embedder = get_embedder()
    vector_store = get_vector_store()
    if _retriever is None and embedder and vector_store:
        try:
            _retriever = Retriever(embedder=embedder, vector_store=vector_store)
            logger.info("✓ Retriever initialized")
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {str(e)}")
            _retriever = None
    return _retriever


def load_file_metadata(file_id: str) -> Optional[Dict[str, Any]]:
    """Load file metadata from JSON file."""
    metadata_file = METADATA_DIR / f"{file_id}.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure loaded data is also serializable (in case it was saved before fixes)
                return make_json_serializable(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading metadata for {file_id}: {str(e)}")
            logger.error(f"Metadata file path: {metadata_file}")
            # Try to read raw content for debugging
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.error(f"File content (first 500 chars): {content[:500]}")
            except:
                pass
            return None
        except Exception as e:
            logger.error(f"Error loading metadata for {file_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    return None


def make_json_serializable(obj):
    """Recursively convert non-JSON-serializable objects to serializable types."""
    import pandas as pd
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (pd.Timestamp, pd.DatetimeTZDtype)):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    # Check for numpy types using safer approach (NumPy 2.0 compatible)
    # Use np.generic to catch all numpy scalar types without referencing deprecated types
    if isinstance(obj, np.generic):
        # Handle numpy scalars - use dtype checking instead of deprecated type names
        try:
            if np.issubdtype(obj.dtype, np.integer):
                return int(obj)
            elif np.issubdtype(obj.dtype, np.floating):
                return float(obj)
            elif np.issubdtype(obj.dtype, np.bool_):
                return bool(obj)
            else:
                # Fallback: try to get the item value
                return obj.item() if hasattr(obj, 'item') else str(obj)
        except (AttributeError, TypeError, ValueError):
            # If dtype check fails, try item() method
            try:
                return obj.item()
            except:
                return str(obj)
    
    # Check for numpy integer/floating abstract base classes (NumPy 2.0 compatible)
    if isinstance(obj, (np.integer, np.floating)):
        try:
            return obj.item()
        except:
            return int(obj) if isinstance(obj, np.integer) else float(obj)
    
    # Handle boolean types
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    
    # Try to detect numpy types by checking if they have 'item' method
    if hasattr(obj, 'item'):
        try:
            item_val = obj.item()
            # Recursively process the item value in case it's also a numpy type
            return make_json_serializable(item_val)
        except (AttributeError, ValueError, TypeError):
            pass
    
    # Handle specific numpy types (NumPy 2.0 compatible - only use types that exist)
    # Avoid np.int_ and np.float_ which were removed in NumPy 2.0
    try:
        # Check for specific numpy integer types
        if isinstance(obj, (np.int8, np.int16, np.int32, np.int64, np.intc, np.intp, np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        # Check for specific numpy float types (avoid np.float_ which was removed)
        elif isinstance(obj, (np.float16, np.float32, np.float64)):
            return float(obj)
    except (AttributeError, TypeError):
        pass
    
    # Final fallback - try to convert to string if all else fails
    try:
        # If it's a basic Python type, return as-is
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        # Otherwise try to convert
        return str(obj)
    except:
        return None


def save_file_metadata(file_id: str, metadata: Dict[str, Any]) -> bool:
    """Save file metadata to JSON file."""
    try:
        metadata_file = METADATA_DIR / f"{file_id}.json"
        # Ensure metadata is JSON serializable before saving
        clean_metadata = make_json_serializable(metadata)
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(clean_metadata, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving metadata for {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return False


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel or CSV file.
    
    Returns:
        File ID and basic metadata
    """
    file_id = None
    saved_file_path = None
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
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
        
        # Read and save file
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        with open(saved_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"File saved: {saved_file_path} ({len(file_content)} bytes)")
        
        # Validate file
        validation_result = file_validator.validate_file(saved_file_path)
        if not validation_result['is_valid']:
            if saved_file_path.exists():
                saved_file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "File validation failed",
                    "errors": validation_result['errors'],
                    "warnings": validation_result['warnings']
                }
            )
        
        # Extract metadata
        try:
            metadata = metadata_extractor.extract_metadata(saved_file_path, include_sample=True)
            
            # Check if metadata extraction returned an error
            if isinstance(metadata, dict) and 'error' in metadata:
                logger.warning(f"Metadata extraction returned error: {metadata.get('error')}")
                # Continue with partial metadata - don't fail upload
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            logger.error(traceback.format_exc())
            # Create minimal metadata instead of failing
            file_stat = saved_file_path.stat()
            metadata = {
                'error': f"Error extracting metadata: {str(e)}",
                'file_name': file.filename,
                'file_type': file_ext.replace('.', ''),
                'file_size_bytes': file_stat.st_size,
                'modified_date': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'sheet_names': [],
                'sheets': {}
            }
        
        # Create file info structure
        file_info = {
            "file_id": file_id,
            "original_filename": file.filename,
            "saved_path": str(saved_file_path),
            "uploaded_at": datetime.now().isoformat(),
            "metadata": metadata,
            "validation": validation_result,
            "user_definitions": {}  # Will be populated by frontend
        }
        
        # Save to registry (in-memory)
        uploaded_files_registry[file_id] = file_info
        
        # Save metadata to JSON file
        save_file_metadata(file_id, file_info)
        
        # Phase 3: Index file in vector store (async, non-blocking)
        try:
            if EMBEDDINGS_AVAILABLE:
                # Index in background (don't block upload response)
                index_file_in_vector_store(file_id, file_info)
        except Exception as e:
            logger.warning(f"Failed to index file {file_id} in vector store: {str(e)}")
            # Don't fail upload if indexing fails
        
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
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error uploading file",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


@app.get("/api/files/list")
async def list_uploaded_files():
    """List all uploaded files."""
    files = []
    
    # Load from JSON files
    for metadata_file in METADATA_DIR.glob("*.json"):
        try:
            file_id = metadata_file.stem
            
            # Skip the relationship cache file - it's not an uploaded file
            if metadata_file.name == "relationship_cache.json":
                continue
            
            # Also skip if it's the cache file by comparing paths
            if RELATIONSHIP_CACHE_FILE.exists():
                try:
                    if metadata_file.samefile(RELATIONSHIP_CACHE_FILE):
                        continue
                except (OSError, ValueError):
                    if str(metadata_file.resolve()) == str(RELATIONSHIP_CACHE_FILE.resolve()):
                        continue
            
            file_info = load_file_metadata(file_id)
            if file_info:
                # Only include files that have a saved_path (real uploaded files)
                # This filters out any cache or system files
                if file_info.get("saved_path"):
                    files.append({
                        "file_id": file_id,
                        "filename": file_info.get("original_filename", "unknown"),
                        "uploaded_at": file_info.get("uploaded_at"),
                        "file_type": file_info.get("metadata", {}).get("file_type"),
                        "sheet_names": file_info.get("metadata", {}).get("sheet_names", [])
                    })
        except Exception as e:
            logger.error(f"Error loading file info from {metadata_file}: {str(e)}")
    
    return {
        "files": files,
        "total": len(files)
    }


@app.get("/api/files/{file_id}")
async def get_file_info(file_id: str):
    """Get detailed information about an uploaded file."""
    try:
        file_info = load_file_metadata(file_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Ensure all data is JSON serializable
        file_info = make_json_serializable(file_info)
        
        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error retrieving file information",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


@app.get("/api/files/{file_id}/columns")
async def get_file_columns(file_id: str, sheet_name: Optional[str] = None):
    """Get columns for a file (and optionally a specific sheet)."""
    file_info = load_file_metadata(file_id)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    metadata = file_info.get("metadata", {})
    sheets = metadata.get("sheets", {})
    user_definitions = file_info.get("user_definitions", {})
    
    if sheet_name:
        # Return columns for specific sheet
        if sheet_name not in sheets:
            raise HTTPException(status_code=404, detail=f"Sheet '{sheet_name}' not found")
        
        sheet_data = sheets[sheet_name]
        columns = []
        
        for col in sheet_data.get("columns", []):
            col_key = f"{sheet_name}::{col}"
            columns.append({
                "name": col,
                "sheet": sheet_name,
                "type": sheet_data.get("column_types", {}).get(col, "unknown"),
                "null_count": sheet_data.get("null_counts", {}).get(col, 0),
                "unique_count": sheet_data.get("unique_counts", {}).get(col, 0),
                "user_definition": user_definitions.get(col_key, "")
            })
        
        return {
            "file_id": file_id,
            "sheet_name": sheet_name,
            "columns": columns
        }
    else:
        # Return columns for all sheets
        all_columns = {}
        
        for sheet_name, sheet_data in sheets.items():
            columns = []
            for col in sheet_data.get("columns", []):
                col_key = f"{sheet_name}::{col}"
                columns.append({
                    "name": col,
                    "sheet": sheet_name,
                    "type": sheet_data.get("column_types", {}).get(col, "unknown"),
                    "null_count": sheet_data.get("null_counts", {}).get(col, 0),
                    "unique_count": sheet_data.get("unique_counts", {}).get(col, 0),
                    "user_definition": user_definitions.get(col_key, "")
                })
            all_columns[sheet_name] = columns
        
        return {
            "file_id": file_id,
            "columns": all_columns
        }


@app.post("/api/files/{file_id}/definitions")
async def save_column_definitions(file_id: str, definitions: Dict[str, str]):
    """
    Save user definitions for columns.
    
    Request body:
    {
        "Sheet1::column_name": "User definition text",
        "Sheet2::column_name": "Another definition"
    }
    """
    file_info = load_file_metadata(file_id)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Update user definitions
    if "user_definitions" not in file_info:
        file_info["user_definitions"] = {}
    
    file_info["user_definitions"].update(definitions)
    file_info["updated_at"] = datetime.now().isoformat()
    
    # Save to JSON file
    if save_file_metadata(file_id, file_info):
        # Update in-memory registry
        uploaded_files_registry[file_id] = file_info
        
        return {
            "status": "success",
            "message": "Column definitions saved successfully",
            "definitions_count": len(file_info["user_definitions"])
        }
    else:
        raise HTTPException(status_code=500, detail="Error saving definitions")


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file and its metadata."""
    try:
        # Get metadata file path
        metadata_file = METADATA_DIR / f"{file_id}.json"
        
        # Check if this is actually the relationship cache file (not just a file with similar name)
        if metadata_file.exists() and RELATIONSHIP_CACHE_FILE.exists():
            try:
                if metadata_file.samefile(RELATIONSHIP_CACHE_FILE):
                    raise HTTPException(status_code=400, detail="Cannot delete system cache file. Use /api/relationships/cache endpoint to clear cache.")
            except (OSError, ValueError):
                # Files might be on different filesystems or samefile might fail, check by name/path
                if str(metadata_file) == str(RELATIONSHIP_CACHE_FILE):
                    raise HTTPException(status_code=400, detail="Cannot delete system cache file. Use /api/relationships/cache endpoint to clear cache.")
        
        file_info = load_file_metadata(file_id)
        
        if not file_info:
            # Try to clean up anyway if metadata file exists (but not if it's the cache file)
            if metadata_file.exists():
                # Double-check it's not the cache file
                if RELATIONSHIP_CACHE_FILE.exists():
                    try:
                        if metadata_file.samefile(RELATIONSHIP_CACHE_FILE):
                            raise HTTPException(status_code=400, detail="Cannot delete system cache file")
                    except (OSError, ValueError):
                        if str(metadata_file) == str(RELATIONSHIP_CACHE_FILE):
                            raise HTTPException(status_code=400, detail="Cannot delete system cache file")
                try:
                    metadata_file.unlink()
                    logger.info(f"Deleted orphaned metadata file: {file_id}")
                except Exception as e:
                    logger.warning(f"Could not delete metadata file {file_id}: {str(e)}")
            
            # Remove from registry if present
            if file_id in uploaded_files_registry:
                del uploaded_files_registry[file_id]
            
            return {
                "status": "success",
                "message": f"File {file_id} metadata cleaned up (file info was missing)"
            }
        
        # Delete physical file (if path exists and is valid)
        saved_path = file_info.get("saved_path")
        if saved_path:
            try:
                file_path = Path(saved_path)
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    logger.info(f"Deleted file: {saved_path}")
                else:
                    logger.warning(f"File path does not exist or is not a file: {saved_path}")
            except Exception as e:
                logger.warning(f"Error deleting physical file {saved_path}: {str(e)}")
                # Continue with metadata deletion even if file deletion fails
        else:
            logger.warning(f"No saved_path in metadata for file {file_id}")
        
        # Delete metadata file
        metadata_file = METADATA_DIR / f"{file_id}.json"
        if metadata_file.exists():
            try:
                metadata_file.unlink()
                logger.info(f"Deleted metadata file: {metadata_file}")
            except Exception as e:
                logger.error(f"Error deleting metadata file {metadata_file}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to delete metadata file: {str(e)}")
        
        # Remove from registry
        if file_id in uploaded_files_registry:
            del uploaded_files_registry[file_id]
        
        # Clear relationship cache if this file was part of cached analysis
        try:
            cache = load_relationship_cache()
            cached_file_ids = cache.get("file_ids", [])
            if file_id in cached_file_ids:
                # Invalidate cache by clearing it
                if RELATIONSHIP_CACHE_FILE.exists():
                    RELATIONSHIP_CACHE_FILE.unlink()
                    logger.info("Relationship cache cleared due to file deletion")
        except Exception as e:
            logger.warning(f"Error clearing relationship cache: {str(e)}")
            # Don't fail deletion if cache clearing fails
        
        return {
            "status": "success",
            "message": f"File {file_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error deleting file",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


# ============================================================================
# Phase 2: Schema Detection & Type Inference API Endpoints
# ============================================================================

@app.post("/api/schema/detect/{file_id}")
async def detect_schema(
    file_id: str,
    sheet_name: Optional[str] = None,
    use_gemini: bool = Query(False, description="Use Gemini API for semantic analysis")
):
    """
    Detect comprehensive schema for an uploaded file.
    
    Args:
        file_id: ID of the uploaded file
        sheet_name: Optional specific sheet to analyze
        use_gemini: Whether to use Gemini API for semantic analysis
        
    Returns:
        Schema detection results with type inference
    """
    try:
        # Load file metadata
        file_info = load_file_metadata(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info["saved_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Get user definitions and transform to format expected by schema_detector
        # schema_detector expects: {column_name: {definition: "...", type: "..."}}
        # but we store: {"file_id::sheet::column": {definition: "..."}}
        raw_user_defs = file_info.get("user_definitions", {})
        schema_user_defs = {}
        
        for col_key, col_def in raw_user_defs.items():
            if isinstance(col_def, dict):
                # Extract column name from key (format: "file_id::sheet::column")
                parts = col_key.split("::")
                if len(parts) >= 3:
                    column_name = parts[2]
                    # If analyzing specific sheet, only include definitions for that sheet
                    if sheet_name is None or parts[1] == sheet_name:
                        schema_user_defs[column_name] = col_def
            elif isinstance(col_def, str):
                # Legacy format: just definition string
                parts = col_key.split("::")
                if len(parts) >= 3:
                    column_name = parts[2]
                    if sheet_name is None or parts[1] == sheet_name:
                        schema_user_defs[column_name] = {"definition": col_def}
        
        # Detect schema
        schema_result = schema_detector.detect_schema(
            file_path=file_path,
            user_definitions=schema_user_defs if schema_user_defs else None,
            sheet_name=sheet_name
        )
        
        # Enhance with Gemini if requested and available
        if use_gemini and gemini_analyzer and gemini_analyzer.enabled:
            try:
                # Load sample data for Gemini analysis
                import pandas as pd
                file_ext = file_path.suffix.lower()
                
                # Load dataframes for all sheets
                dfs = {}
                if file_ext in ['.xlsx', '.xls']:
                    excel_file = pd.ExcelFile(file_path)
                    for sheet in excel_file.sheet_names:
                        dfs[sheet] = pd.read_excel(excel_file, sheet_name=sheet, nrows=100)
                    excel_file.close()
                else:
                    dfs['Sheet1'] = pd.read_csv(file_path, nrows=100)
                
                # Enhance each column with Gemini analysis
                for sheet_name_key, sheet_schema in schema_result.get('sheets', {}).items():
                    df = dfs.get(sheet_name_key)
                    if df is None:
                        continue
                    
                    # Get user definitions for this specific sheet
                    sheet_user_defs = {}
                    for col_key, col_def in raw_user_defs.items():
                        parts = col_key.split("::")
                        if len(parts) >= 3 and parts[1] == sheet_name_key:
                            column_name = parts[2]
                            if isinstance(col_def, dict):
                                sheet_user_defs[column_name] = col_def
                            else:
                                sheet_user_defs[column_name] = {"definition": str(col_def)}
                    
                    for col_name, col_schema in sheet_schema.get('columns', {}).items():
                        if col_name not in df.columns:
                            continue
                            
                        sample_values = df[col_name].dropna().head(20).tolist()
                        
                        # Get user definition for this column from sheet-specific definitions
                        user_def_for_gemini = sheet_user_defs.get(col_name)
                        
                        gemini_result = gemini_analyzer.analyze_column_semantics(
                            column_name=col_name,
                            sample_values=sample_values,
                            detected_type=col_schema.get('detected_type', 'unknown'),
                            user_definition=user_def_for_gemini
                        )
                        
                        # Merge Gemini results
                        col_schema['gemini_analysis'] = gemini_result
                        if gemini_result.get('semantic_type') != 'unknown':
                            col_schema['semantic_type'] = gemini_result.get('semantic_type')
                            col_schema['description'] = gemini_result.get('description')
                
                # Detect relationships with Gemini for each sheet
                for sheet_name_key, sheet_schema in schema_result.get('sheets', {}).items():
                    try:
                        # Get columns for this sheet
                        columns_list = []
                        for col_name, col_schema in sheet_schema.get('columns', {}).items():
                            columns_list.append({
                                'column_name': col_name,
                                'detected_type': col_schema.get('detected_type', 'unknown'),
                                'semantic_meaning': col_schema.get('semantic_meaning', col_schema.get('semantic_type', 'unknown')),
                                'description': col_schema.get('description', '')
                            })
                        
                        # Get sample data for this sheet
                        if sheet_name_key in df.columns or len(df) > 0:
                            sample_data = df.head(10).to_dict('records')
                        else:
                            sample_data = []
                        
                        # Try Gemini relationships, but don't fail if it errors
                        gemini_relationships = []
                        try:
                            gemini_relationships = gemini_analyzer.analyze_relationships(
                                columns=columns_list,
                                sample_data=sample_data
                            )
                            
                            # Add Gemini relationships
                            if 'relationships' not in sheet_schema:
                                sheet_schema['relationships'] = []
                            sheet_schema['relationships'].extend(gemini_relationships)
                        except Exception as rel_error:
                            logger.warning(f"Gemini relationship analysis failed for sheet {sheet_name_key}: {str(rel_error)}")
                            # Continue without Gemini relationships - schema detector will still find basic relationships
                    except Exception as sheet_error:
                        logger.warning(f"Error processing sheet {sheet_name_key} with Gemini: {str(sheet_error)}")
                        continue
                
            except Exception as e:
                logger.warning(f"Gemini analysis failed: {str(e)}")
                schema_result['gemini_warning'] = f"Gemini analysis failed: {str(e)}"
        
        schema_result['file_id'] = file_id
        schema_result['original_filename'] = file_info.get('original_filename', 'unknown')
        
        return schema_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting schema for {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error detecting schema",
                "error": str(e)
            }
        )


@app.get("/api/schema/analyze/{file_id}")
async def analyze_schema(
    file_id: str,
    sheet_name: Optional[str] = None
):
    """
    Get comprehensive schema analysis including visualizations data.
    
    Returns:
        Schema analysis with statistics ready for frontend visualization
    """
    try:
        # Load file metadata
        file_info = load_file_metadata(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Detect schema
        schema_result = await detect_schema(file_id, sheet_name, use_gemini=True)
        
        if 'error' in schema_result:
            raise HTTPException(status_code=500, detail=schema_result['error'])
        
        # Prepare visualization data
        visualization_data = {
            'file_id': file_id,
            'filename': file_info.get('original_filename', 'unknown'),
            'type_distribution': {},
            'data_quality_metrics': {},
            'column_statistics': [],
            'relationships': []
        }
        
        # Aggregate data across sheets
        for sheet_name_key, sheet_schema in schema_result.get('sheets', {}).items():
            # Type distribution
            type_counts = {}
            for col_name, col_schema in sheet_schema.get('columns', {}).items():
                col_type = col_schema.get('detected_type', 'unknown')
                type_counts[col_type] = type_counts.get(col_type, 0) + 1
            
            visualization_data['type_distribution'][sheet_name_key] = type_counts
            
            # Data quality
            visualization_data['data_quality_metrics'][sheet_name_key] = sheet_schema.get('data_quality', {})
            
            # Column statistics
            for col_name, col_schema in sheet_schema.get('columns', {}).items():
                visualization_data['column_statistics'].append({
                    'sheet': sheet_name_key,
                    'column': col_name,
                    'type': col_schema.get('detected_type', 'unknown'),
                    'subtype': col_schema.get('subtype'),
                    'null_percentage': col_schema.get('null_percentage', 0),
                    'unique_percentage': col_schema.get('unique_percentage', 0),
                    'confidence': col_schema.get('confidence', 0),
                    'semantic_meaning': col_schema.get('semantic_meaning', 'unknown'),
                    'statistics': col_schema.get('statistics', {})
                })
            
            # Relationships
            relationships = sheet_schema.get('relationships', [])
            visualization_data['relationships'].extend([
                {**rel, 'sheet': sheet_name_key} for rel in relationships
            ])
        
        # Prepare network graph data (nodes and links)
        nodes = []
        links = []
        node_map = {}
        
        # Add nodes (columns)
        for col_stat in visualization_data['column_statistics']:
            col_id = f"{col_stat['sheet']}::{col_stat['column']}"
            if col_id not in node_map:
                node_map[col_id] = len(nodes)
                nodes.append({
                    'id': col_id,
                    'label': col_stat['column'],
                    'sheet': col_stat['sheet'],
                    'type': col_stat['type'],
                    'semantic': col_stat.get('semantic_meaning', 'unknown'),
                    'group': col_stat['type']  # For color grouping
                })
        
        # Add links (relationships)
        for rel in visualization_data['relationships']:
            source_col = rel.get('source_column', rel.get('column', ''))
            target_col = rel.get('target_column', '')
            rel_sheet = rel.get('sheet', 'Sheet1')
            
            if source_col and target_col:
                source_id = f"{rel_sheet}::{source_col}"
                target_id = f"{rel_sheet}::{target_col}"
                
                if source_id in node_map and target_id in node_map:
                    links.append({
                        'source': node_map[source_id],
                        'target': node_map[target_id],
                        'type': rel.get('type', 'unknown'),
                        'label': rel.get('description', ''),
                        'confidence': rel.get('confidence', 0.5),
                        'direction': rel.get('direction', 'source_to_target')
                    })
        
        visualization_data['network_graph'] = {
            'nodes': nodes,
            'links': links
        }
        
        return {
            'schema': schema_result,
            'visualization': visualization_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing schema for {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error analyzing schema",
                "error": str(e)
            }
        )


# ============================================================================
# Column Definitions Management API
# ============================================================================

RELATIONSHIP_CACHE_FILE = METADATA_DIR / "relationship_cache.json"

def load_relationship_cache() -> Dict[str, Any]:
    """Load cached relationship analysis results."""
    if RELATIONSHIP_CACHE_FILE.exists():
        try:
            with open(RELATIONSHIP_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading relationship cache: {str(e)}")
            return {}
    return {}

def save_relationship_cache(cache_data: Dict[str, Any]) -> bool:
    """Save relationship analysis cache."""
    try:
        with open(RELATIONSHIP_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving relationship cache: {str(e)}")
        return False

@app.get("/api/column-definitions")
async def get_all_column_definitions():
    """Get all column definitions across all files."""
    try:
        all_definitions = {}
        for file_id in uploaded_files_registry.keys():
            file_info = load_file_metadata(file_id)
            if file_info:
                user_defs = file_info.get("user_definitions", {})
                for col_key, definition in user_defs.items():
                    all_definitions[f"{file_id}::{col_key}"] = {
                        "file_id": file_id,
                        "column_key": col_key,
                        "definition": definition
                    }
        return {"definitions": all_definitions}
    except Exception as e:
        logger.error(f"Error getting column definitions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/column-definitions")
async def save_column_definition(definition_data: Dict[str, Any]):
    """Save or update a column definition."""
    try:
        file_id = definition_data.get("file_id")
        column_key = definition_data.get("column_key")
        definition = definition_data.get("definition", "")
        
        if not file_id or not column_key:
            raise HTTPException(status_code=400, detail="file_id and column_key are required")
        
        file_info = load_file_metadata(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        if "user_definitions" not in file_info:
            file_info["user_definitions"] = {}
        
        file_info["user_definitions"][column_key] = definition
        uploaded_files_registry[file_id] = file_info
        
        if save_file_metadata(file_id, file_info):
            return {"success": True, "message": "Definition saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save definition")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving column definition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/column-definitions/{file_id}/{column_key:path}")
async def delete_column_definition(file_id: str, column_key: str):
    """Delete a column definition."""
    try:
        file_info = load_file_metadata(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        user_defs = file_info.get("user_definitions", {})
        if column_key in user_defs:
            del user_defs[column_key]
            file_info["user_definitions"] = user_defs
            uploaded_files_registry[file_id] = file_info
            
            if save_file_metadata(file_id, file_info):
                return {"success": True, "message": "Definition deleted"}
            else:
                raise HTTPException(status_code=500, detail="Failed to delete definition")
        else:
            return {"success": True, "message": "Definition not found (already deleted)"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting column definition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/relationships/analyze-all")
async def analyze_all_relationships():
    """
    Analyze relationships across ALL files at once.
    Uses Gemini with all column definitions and metadata.
    Results are cached and updated only when needed.
    """
    try:
        logger.info("Starting batch relationship analysis across all files...")
        
        # Collect all files and their metadata
        all_files_data = []
        all_column_definitions = {}
        
        for file_id in uploaded_files_registry.keys():
            file_info = load_file_metadata(file_id)
            if not file_info:
                continue
            
            # Get columns for this file (extract directly from metadata)
            try:
                metadata = file_info.get("metadata", {})
                sheets = metadata.get("sheets", {})
                user_defs = file_info.get("user_definitions", {})
                
                # Build columns structure
                columns_by_sheet = {}
                for sheet_name, sheet_data in sheets.items():
                    columns = []
                    for col in sheet_data.get("columns", []):
                        col_key = f"{sheet_name}::{col}"
                        columns.append({
                            "name": col,
                            "sheet": sheet_name,
                            "type": sheet_data.get("column_types", {}).get(col, "unknown"),
                            "null_count": sheet_data.get("null_counts", {}).get(col, 0),
                            "unique_count": sheet_data.get("unique_counts", {}).get(col, 0),
                            "user_definition": user_defs.get(col_key, "")
                        })
                    columns_by_sheet[sheet_name] = columns
                
                # Collect column definitions
                for col_key, definition in user_defs.items():
                    all_column_definitions[f"{file_id}::{col_key}"] = definition
                
                all_files_data.append({
                    "file_id": file_id,
                    "filename": file_info.get("original_filename", "unknown"),
                    "columns": columns_by_sheet,
                    "user_definitions": user_defs,
                    "metadata": metadata
                })
            except Exception as e:
                logger.warning(f"Error processing file {file_id}: {str(e)}")
                continue
        
        if not all_files_data:
            return {
                "success": False,
                "message": "No files found for analysis",
                "relationships": [],
                "cached": False
            }
        
        # Check cache
        cache = load_relationship_cache()
        cache_key = "all_files_relationships"
        
        # Check if cache is valid (has all current files)
        cached_file_ids = set(cache.get("file_ids", []))
        current_file_ids = set([f["file_id"] for f in all_files_data])
        
        if cached_file_ids == current_file_ids and cache.get(cache_key):
            logger.info("Using cached relationship analysis")
            return {
                "success": True,
                "message": "Using cached results",
                "relationships": cache.get(cache_key, []),
                "cached": True,
                "analyzed_at": cache.get("analyzed_at"),
                "file_count": len(all_files_data)
            }
        
        # ========================================================================
        # PHASE 1: PRIORITY - Gemini AI Analysis (Primary Method)
        # ========================================================================
        logger.info(f"PHASE 1: Starting Gemini AI analysis across {len(all_files_data)} files...")
        
        relationships = []
        gemini_success = False
        gemini_relationships = []
        
        if gemini_analyzer and gemini_analyzer.enabled:
            try:
                # Prepare comprehensive data for Gemini
                columns_summary = []
                for file_data in all_files_data:
                    file_cols = []
                    for sheet_name, columns in file_data["columns"].items():
                        for col in columns:
                            col_key = f"{sheet_name}::{col['name']}"
                            user_def = file_data["user_definitions"].get(col_key, "")
                            file_cols.append({
                                "file": file_data["filename"],
                                "sheet": sheet_name,
                                "column": col["name"],
                                "type": col.get("type", "unknown"),
                                "user_definition": user_def
                            })
                    columns_summary.extend(file_cols)
                
                # Prepare columns format for Gemini with full context
                gemini_columns = []
                for col in columns_summary:
                    gemini_columns.append({
                        "name": f"{col['file']}::{col['sheet']}::{col['column']}",
                        "column_name": f"{col['file']}::{col['sheet']}::{col['column']}",  # For compatibility
                        "type": col["type"],
                        "detected_type": col["type"],  # For compatibility
                        "user_definition": col.get("user_definition", "")
                    })
                
                # Get sample data for context (first few rows from each file)
                sample_data = []
                for file_data in all_files_data[:5]:  # Limit to first 5 files for context
                    try:
                        file_path = Path(file_data["metadata"].get("saved_path", ""))
                        if file_path.exists():
                            loader = ExcelLoader()
                            df = loader.load_file(file_path)
                            if df is not None and not df.empty:
                                sample_data.append({
                                    "file": file_data["filename"],
                                    "sample_rows": df.head(3).to_dict('records')
                                })
                    except Exception as e:
                        logger.debug(f"Could not load sample data for {file_data['filename']}: {str(e)}")
                        pass
                
                # Call Gemini for batch relationship analysis (PRIORITY)
                logger.info("Calling Gemini API for relationship analysis...")
                gemini_relationships = gemini_analyzer.analyze_relationships(
                    columns=gemini_columns,
                    sample_data=sample_data if sample_data else None
                )
                
                if gemini_relationships and len(gemini_relationships) > 0:
                    # Mark Gemini relationships with priority and source
                    for rel in gemini_relationships:
                        rel["source"] = "gemini_ai"
                        rel["priority"] = "high"
                        # Ensure confidence is set (Gemini provides this)
                        if "confidence" not in rel:
                            rel["confidence"] = 0.85  # Default high confidence for Gemini
                    
                    relationships.extend(gemini_relationships)
                    gemini_success = True
                    logger.info(f"✓ Gemini AI analysis complete: Found {len(gemini_relationships)} relationships")
                else:
                    logger.warning("Gemini returned empty results, will use statistical patterns")
                    
            except Exception as e:
                logger.error(f"✗ Gemini AI analysis failed: {str(e)}")
                logger.info("Falling back to statistical pattern analysis...")
        else:
            logger.warning("Gemini analyzer not available, using statistical patterns only")
        
        # ========================================================================
        # PHASE 2: SUPPLEMENTARY - Statistical Pattern Analysis
        # ========================================================================
        logger.info("PHASE 2: Running statistical pattern analysis to supplement results...")
        
        statistical_relationships = []
        for file_data in all_files_data:
            try:
                file_path = Path(file_data["metadata"].get("saved_path", ""))
                if file_path.exists():
                    # Detect schema for this file (without Gemini to avoid duplicate calls)
                    schema_result = await detect_schema(file_data["file_id"], None, use_gemini=False)
                    
                    for sheet_name, sheet_schema in schema_result.get("sheets", {}).items():
                        sheet_relationships = sheet_schema.get("relationships", [])
                        for rel in sheet_relationships:
                            # Add file context and mark as statistical
                            rel["file_id"] = file_data["file_id"]
                            rel["file_name"] = file_data["filename"]
                            rel["sheet"] = sheet_name
                            rel["source"] = "statistical_pattern"
                            rel["priority"] = "medium"
                            # Ensure confidence is set
                            if "confidence" not in rel:
                                rel["confidence"] = 0.65  # Default medium confidence for statistical
                            
                            statistical_relationships.append(rel)
            except Exception as e:
                logger.warning(f"Error detecting statistical relationships for {file_data['file_id']}: {str(e)}")
        
        # Merge statistical relationships, avoiding duplicates with Gemini results
        if statistical_relationships:
            logger.info(f"✓ Statistical analysis complete: Found {len(statistical_relationships)} relationships")
            
            # Add statistical relationships that don't duplicate Gemini ones
            if gemini_success:
                # Create a set of Gemini relationship keys for deduplication
                gemini_keys = set()
                for rel in gemini_relationships:
                    key = f"{rel.get('source_column', rel.get('column', ''))}::{rel.get('target_column', '')}::{rel.get('type', '')}"
                    gemini_keys.add(key)
                
                # Only add statistical relationships that are new
                added_count = 0
                for stat_rel in statistical_relationships:
                    stat_key = f"{stat_rel.get('source_column', stat_rel.get('column', ''))}::{stat_rel.get('target_column', '')}::{stat_rel.get('type', '')}"
                    if stat_key not in gemini_keys:
                        relationships.append(stat_rel)
                        added_count += 1
                
                logger.info(f"Added {added_count} additional statistical relationships (avoided {len(statistical_relationships) - added_count} duplicates)")
            else:
                # If Gemini failed, use all statistical relationships
                relationships.extend(statistical_relationships)
                logger.info(f"Using all {len(statistical_relationships)} statistical relationships (Gemini unavailable)")
        
        # Summary log and analysis breakdown
        gemini_count = len([r for r in relationships if r.get("source") == "gemini_ai"])
        statistical_count = len([r for r in relationships if r.get("source") == "statistical_pattern"])
        
        # Group relationships by type, strength, and impact for better insights
        relationships_by_type = {}
        relationships_by_strength = {"strong": 0, "medium": 0, "weak": 0}
        relationships_by_impact = {"critical": 0, "important": 0, "informational": 0}
        cross_file_count = 0
        
        for rel in relationships:
            rel_type = rel.get("type", "unknown")
            relationships_by_type[rel_type] = relationships_by_type.get(rel_type, 0) + 1
            
            strength = rel.get("strength", "medium")
            if strength in relationships_by_strength:
                relationships_by_strength[strength] += 1
            
            impact = rel.get("impact", "informational")
            if impact in relationships_by_impact:
                relationships_by_impact[impact] += 1
            
            # Check if it's a cross-file relationship
            source_col = rel.get("source_column", rel.get("column", ""))
            target_col = rel.get("target_column", "")
            if source_col and target_col:
                source_file = source_col.split("::")[0] if "::" in source_col else ""
                target_file = target_col.split("::")[0] if "::" in target_col else ""
                if source_file and target_file and source_file != target_file:
                    cross_file_count += 1
        
        logger.info(f"Relationship analysis summary: {gemini_count} from Gemini AI, {statistical_count} from statistical patterns, {len(relationships)} total ({cross_file_count} cross-file)")
        
        # Save to cache
        cache_data = {
            "file_ids": list(current_file_ids),
            "analyzed_at": datetime.now().isoformat(),
            "all_files_relationships": relationships,
            "file_count": len(all_files_data)
        }
        save_relationship_cache(cache_data)
        
        # Prepare summary message
        if gemini_success:
            message = f"Analyzed {len(all_files_data)} files: {gemini_count} relationships from Gemini AI, {statistical_count} from statistical patterns. Found {cross_file_count} cross-file relationships."
        else:
            message = f"Analyzed {len(all_files_data)} files: {statistical_count} relationships from statistical patterns (Gemini unavailable)"
        
        return {
            "success": True,
            "message": message,
            "relationships": relationships,
            "cached": False,
            "analyzed_at": cache_data["analyzed_at"],
            "file_count": len(all_files_data),
            "analysis_summary": {
                "gemini_count": gemini_count,
                "statistical_count": statistical_count,
                "total_count": len(relationships),
                "gemini_success": gemini_success,
                "cross_file_count": cross_file_count,
                "by_type": relationships_by_type,
                "by_strength": relationships_by_strength,
                "by_impact": relationships_by_impact
            }
        }
        
    except Exception as e:
        logger.error(f"Error in batch relationship analysis: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/relationships/cached")
async def get_cached_relationships():
    """Get cached relationship analysis results."""
    try:
        cache = load_relationship_cache()
        return {
            "success": True,
            "relationships": cache.get("all_files_relationships", []),
            "analyzed_at": cache.get("analyzed_at"),
            "file_count": cache.get("file_count", 0),
            "cached": True
        }
    except Exception as e:
        logger.error(f"Error getting cached relationships: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/relationships/cache")
async def clear_relationship_cache():
    """Clear relationship analysis cache (forces re-analysis)."""
    try:
        if RELATIONSHIP_CACHE_FILE.exists():
            RELATIONSHIP_CACHE_FILE.unlink()
        return {"success": True, "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
# ============================================
# Phase 3: Semantic Indexing & RAG Endpoints
# ===========================================

def index_file_in_vector_store(file_id: str, file_info: Dict[str, Any]) -> bool:
    """
    Index a file's columns and metadata into the vector store using full excel_parser capabilities.
    
    This function:
    1. Uses schema detection results (if available) or triggers schema detection
    2. Incorporates user-provided column definitions
    3. Includes Gemini semantic analysis results
    4. Indexes relationship information
    
    Args:
        file_id: File ID
        file_info: File information dictionary
        
    Returns:
        True if successful, False otherwise
    """
    if not EMBEDDINGS_AVAILABLE:
        return False
    
    try:
        embedder = get_embedder()
        vector_store = get_vector_store()
        
        if not embedder or not vector_store:
            logger.warning("Embeddings not available - skipping indexing")
            return False
        
        file_name = file_info.get("original_filename", "unknown")
        saved_path = file_info.get("saved_path")
        user_definitions = file_info.get("user_definitions", {})
        
        # Check if we have schema detection results, if not, run schema detection
        schema_result = None
        if saved_path and Path(saved_path).exists():
            try:
                # Prepare user_definitions in format expected by schema_detector
                # schema_detector expects: {column_name: {definition: "...", type: "..."}}
                # but we store: {"file_id::sheet::column": {definition: "..."}}
                schema_user_defs = {}
                for col_key, col_def in user_definitions.items():
                    if isinstance(col_def, dict):
                        # Extract column name from key (format: "file_id::sheet::column")
                        parts = col_key.split("::")
                        if len(parts) >= 3:
                            column_name = parts[2]
                            schema_user_defs[column_name] = col_def
                    elif isinstance(col_def, str):
                        # Legacy format: just definition string
                        parts = col_key.split("::")
                        if len(parts) >= 3:
                            column_name = parts[2]
                            schema_user_defs[column_name] = {"definition": col_def}
                
                # Run schema detection with user definitions
                schema_result = schema_detector.detect_schema(
                    file_path=Path(saved_path),
                    user_definitions=schema_user_defs if schema_user_defs else None
                )
                
                # Enhance with Gemini if available
                if gemini_analyzer and gemini_analyzer.enabled:
                    try:
                        import pandas as pd
                        file_ext = Path(saved_path).suffix.lower()
                        
                        # Load sample data for Gemini
                        if file_ext in ['.xlsx', '.xls']:
                            excel_file = pd.ExcelFile(saved_path)
                            dfs = {sheet: pd.read_excel(excel_file, sheet_name=sheet, nrows=100) 
                                   for sheet in excel_file.sheet_names}
                            excel_file.close()
                        else:
                            dfs = {'Sheet1': pd.read_csv(saved_path, nrows=100)}
                        
                        # Enhance each column with Gemini analysis
                        for sheet_name_key, sheet_schema in schema_result.get('sheets', {}).items():
                            df = dfs.get(sheet_name_key)
                            if df is None:
                                continue
                                
                            for col_name, col_schema in sheet_schema.get('columns', {}).items():
                                if col_name not in df.columns:
                                    continue
                                    
                                sample_values = df[col_name].dropna().head(20).tolist()
                                
                                # Get user definition for this column
                                col_key = f"{file_id}::{sheet_name_key}::{col_name}"
                                user_def_dict = user_definitions.get(col_key, {})
                                if isinstance(user_def_dict, dict):
                                    user_def_for_gemini = user_def_dict
                                else:
                                    user_def_for_gemini = None
                                
                                gemini_result = gemini_analyzer.analyze_column_semantics(
                                    column_name=col_name,
                                    sample_values=sample_values,
                                    detected_type=col_schema.get('detected_type', 'unknown'),
                                    user_definition=user_def_for_gemini
                                )
                                
                                # Merge Gemini results
                                col_schema['gemini_analysis'] = gemini_result
                                if gemini_result.get('semantic_type') != 'unknown':
                                    col_schema['semantic_type'] = gemini_result.get('semantic_type')
                                if gemini_result.get('description'):
                                    col_schema['description'] = gemini_result.get('description')
                    except Exception as gemini_error:
                        logger.warning(f"Gemini enhancement failed during indexing: {str(gemini_error)}")
                        # Continue without Gemini - schema detection results are still valuable
            except Exception as schema_error:
                logger.warning(f"Schema detection failed during indexing: {str(schema_error)}")
                # Fall back to basic metadata
                schema_result = None
        
        # Use schema results if available, otherwise fall back to basic metadata
        if schema_result and schema_result.get('sheets'):
            # Use rich schema detection results
            indexed_count = 0
            
            for sheet_name, sheet_schema in schema_result.get('sheets', {}).items():
                columns_dict = sheet_schema.get('columns', {})
                
                for column_name, col_schema in columns_dict.items():
                    # Extract all available information
                    detected_type = col_schema.get('detected_type', 'unknown')
                    semantic_type = col_schema.get('semantic_type', col_schema.get('semantic_meaning', ''))
                    description = col_schema.get('description', '')
                    confidence = col_schema.get('confidence', 0.0)
                    stats = col_schema.get('statistics', {})
                    
                    # Get user definition
                    col_key = f"{file_id}::{sheet_name}::{column_name}"
                    user_def_data = user_definitions.get(col_key, {})
                    if isinstance(user_def_data, dict):
                        user_def = user_def_data.get("definition", "")
                    else:
                        user_def = str(user_def_data) if user_def_data else ""
                    
                    # Get sample values from stats or metadata
                    sample_values = []
                    if stats.get('sample_values'):
                        sample_values = [str(v) for v in stats['sample_values'][:10]]
                    elif col_schema.get('sample_values'):
                        sample_values = [str(v) for v in col_schema['sample_values'][:10]]
                    
                    # Build rich description combining all sources
                    rich_description = description
                    if not rich_description and semantic_type:
                        rich_description = f"Semantic type: {semantic_type}"
                    if not rich_description and user_def:
                        rich_description = user_def
                    
                    # Generate embedding with all metadata
                    col_metadata = embedder.embed_column_metadata(
                        column_name=column_name,
                        column_type=detected_type,
                        description=rich_description,
                        user_definition=user_def,
                        sample_values=sample_values
                    )
                    
                    # Add statistics and confidence to metadata
                    col_metadata['confidence'] = confidence
                    col_metadata['statistics'] = stats
                    col_metadata['semantic_type'] = semantic_type
                    
                    # Add to vector store
                    vector_store.add_column(
                        file_id=file_id,
                        file_name=file_name,
                        sheet_name=sheet_name,
                        column_name=column_name,
                        embedding=col_metadata["context_embedding"],
                        metadata=col_metadata
                    )
                    indexed_count += 1
                
                # Index relationships for this sheet
                relationships = sheet_schema.get('relationships', [])
                for rel in relationships:
                    try:
                        rel_embedding_data = embedder.embed_relationship(rel)
                        vector_store.add_relationship(
                            relationship=rel,
                            embedding=rel_embedding_data["embedding"]
                        )
                    except Exception as rel_error:
                        logger.warning(f"Failed to index relationship: {str(rel_error)}")
                        continue
            
            logger.info(f"Indexed {indexed_count} columns and {len(relationships)} relationships for file: {file_id}")
        else:
            # Fallback to basic metadata extraction
            metadata = file_info.get("metadata", {})
            sheets = metadata.get("sheets", {})
            indexed_count = 0
            
            for sheet_name, sheet_data in sheets.items():
                columns = sheet_data.get("columns", [])
                
                for col in columns:
                    column_name = col.get("name", "")
                    if not column_name:
                        continue
                    
                    # Get user definition
                    col_key = f"{file_id}::{sheet_name}::{column_name}"
                    user_def_data = user_definitions.get(col_key, {})
                    if isinstance(user_def_data, dict):
                        user_def = user_def_data.get("definition", "")
                    else:
                        user_def = str(user_def_data) if user_def_data else ""
                    
                    # Get sample values
                    sample_data = col.get("sample_data", [])
                    sample_values = [str(v) for v in sample_data[:10]] if sample_data else []
                    
                    # Generate embedding metadata
                    col_metadata = embedder.embed_column_metadata(
                        column_name=column_name,
                        column_type=col.get("type", "unknown"),
                        description=col.get("description", ""),
                        user_definition=user_def,
                        sample_values=sample_values
                    )
                    
                    # Add to vector store
                    vector_store.add_column(
                        file_id=file_id,
                        file_name=file_name,
                        sheet_name=sheet_name,
                        column_name=column_name,
                        embedding=col_metadata["context_embedding"],
                        metadata=col_metadata
                    )
                    indexed_count += 1
            
            logger.info(f"Indexed {indexed_count} columns (basic metadata) for file: {file_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error indexing file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return False


@app.post("/api/semantic/index/{file_id}")
async def index_file(file_id: str):
    """Index a file into the semantic vector store."""
    try:
        file_info = load_file_metadata(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        success = index_file_in_vector_store(file_id, file_info)
        
        if success:
            return {
                "success": True,
                "message": f"File {file_id} indexed successfully",
                "file_id": file_id
            }
        else:
            return {
                "success": False,
                "message": "Indexing failed - embeddings not available",
                "file_id": file_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/semantic/index-all")
async def index_all_files():
    """Index all uploaded files into the semantic vector store."""
    try:
        if not EMBEDDINGS_AVAILABLE:
            return {
                "success": False,
                "message": "Embeddings module not available",
                "indexed": 0,
                "total": 0
            }
        
        # Get all files
        files_response = await list_uploaded_files()
        files = files_response.get("files", [])
        
        indexed_count = 0
        failed_count = 0
        
        for file_info in files:
            file_id = file_info.get("file_id")
            if file_id:
                full_info = load_file_metadata(file_id)
                if full_info:
                    if index_file_in_vector_store(file_id, full_info):
                        indexed_count += 1
                    else:
                        failed_count += 1
        
        return {
            "success": True,
            "message": f"Indexed {indexed_count} files, {failed_count} failed",
            "indexed": indexed_count,
            "failed": failed_count,
            "total": len(files)
        }
    except Exception as e:
        logger.error(f"Error indexing all files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/semantic/search")
async def semantic_search(
    query: str = Query(..., description="Natural language query"),
    n_results: int = Query(10, ge=1, le=50, description="Number of results"),
    file_id: Optional[str] = Query(None, description="Filter by file ID")
):
    """Perform semantic search over indexed Excel data."""
    try:
        retriever = get_retriever()
        if not retriever:
            raise HTTPException(
                status_code=503,
                detail="Semantic search not available - embeddings not initialized"
            )
        
        # Retrieve context
        context = retriever.retrieve_context(
            query=query,
            n_columns=n_results,
            n_relationships=min(5, n_results // 2),
            file_filter=file_id
        )
        
        return {
            "success": True,
            "query": query,
            "results": context,
            "total_columns": len(context["columns"]),
            "total_relationships": len(context["relationships"])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/semantic/stats")
async def get_vector_store_stats():
    """Get statistics about the vector store."""
    try:
        vector_store = get_vector_store()
        if not vector_store:
            return {
                "available": False,
                "message": "Vector store not initialized"
            }
        
        stats = vector_store.get_collection_stats()
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting vector store stats: {str(e)}")
        return {
            "available": False,
            "error": str(e)
        }


@app.delete("/api/semantic/index/{file_id}")
async def remove_file_from_index(file_id: str):
    """Remove a file from the semantic index."""
    try:
        vector_store = get_vector_store()
        if not vector_store:
            raise HTTPException(
                status_code=503,
                detail="Vector store not available"
            )
        
        success = vector_store.delete_file(file_id)
        
        if success:
            return {
                "success": True,
                "message": f"File {file_id} removed from index"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to remove file {file_id} from index"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing file from index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 4: LangChain Agent System Endpoints
# ============================================================================

# Global agent instances (one per provider)
_agent_instances = {}

def get_agent_tools():
    """Get common tools for all agents."""
    excel_retriever = ExcelRetriever(
        files_base_path=UPLOADED_FILES_DIR,
        metadata_base_path=METADATA_DIR
    )
    data_calculator = DataCalculator()
    trend_analyzer = TrendAnalyzer()
    comparative_analyzer = ComparativeAnalyzer()
    kpi_calculator = KPICalculator()
    graph_generator = GraphGenerator()
    
    # Get semantic retriever
    semantic_retriever = get_retriever()
    if not semantic_retriever:
        logger.warning("Semantic retriever not available - agent will have limited capabilities")
    
    # Create LangChain tools
    tools = []
    
    if semantic_retriever:
        tools.append(create_excel_retriever_tool(excel_retriever, semantic_retriever))
    tools.append(create_data_calculator_tool(data_calculator))
    tools.append(create_trend_analyzer_tool(trend_analyzer, excel_retriever, semantic_retriever))
    tools.append(create_comparative_analyzer_tool(comparative_analyzer, excel_retriever, semantic_retriever))
    tools.append(create_kpi_calculator_tool(kpi_calculator, excel_retriever, semantic_retriever))
    tools.append(create_graph_generator_tool(graph_generator, excel_retriever, semantic_retriever))
    
    return tools

def get_agent_instance(provider: str = "groq"):
    """Get or create agent instance for specified provider."""
    global _agent_instances
    
    if not AGENT_AVAILABLE:
        return None
    
    provider = provider.lower()
    
    # Return cached instance if available
    if provider in _agent_instances and _agent_instances[provider] is not None:
        return _agent_instances[provider]
    
    try:
        # Get tools
        tools = get_agent_tools()
        
        # Create agent based on provider
        if provider == "gemini":
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.error("GEMINI_API_KEY not found in environment variables")
                raise ValueError("GEMINI_API_KEY is required for Gemini agent")
            
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            
            _agent_instances[provider] = ExcelAgent(
                tools=tools,
                provider="gemini",
                model_name=model_name,
                gemini_api_key=gemini_api_key
            )
            logger.info(f"✓ Gemini agent initialized successfully with model: {model_name}")
            
        elif provider == "groq":
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("GROQ_API_KEY not found in environment variables")
                raise ValueError("GROQ_API_KEY is required for Groq agent")
            
            model_name = os.getenv("AGENT_MODEL_NAME", "meta-llama/llama-4-maverick-17b-128e-instruct")
            
            _agent_instances[provider] = ExcelAgent(
                tools=tools,
                provider="groq",
                model_name=model_name,
                groq_api_key=groq_api_key
            )
            logger.info(f"✓ Groq agent initialized successfully with model: {model_name}")
        else:
            raise ValueError(f"Unknown provider: {provider}. Must be 'groq' or 'gemini'")
        
    except Exception as e:
        logger.error(f"Failed to initialize {provider} agent: {str(e)}")
        _agent_instances[provider] = None
        return None
    
    return _agent_instances[provider]


class AgentQueryRequest(BaseModel):
    """Request model for agent query."""
    question: str
    provider: Optional[str] = "groq"  # "groq" or "gemini"


@app.post("/api/agent/query")
async def agent_query(request: AgentQueryRequest):
    """Process a natural language query using the agent."""
    try:
        if not AGENT_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Agent system not available - dependencies not installed"
            )
        
        provider = request.provider.lower() if request.provider else "groq"
        if provider not in ["groq", "gemini"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {provider}. Must be 'groq' or 'gemini'"
            )
        
        agent = get_agent_instance(provider=provider)
        if not agent:
            raise HTTPException(
                status_code=503,
                detail=f"{provider.capitalize()} agent not initialized - check logs and API keys"
            )
        
        # Process query
        result = agent.query(request.question)
        result["provider"] = provider
        result["model_name"] = agent.model_name
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing agent query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/status")
async def get_agent_status():
    """Get agent system status for all providers."""
    try:
        prompt_eng_available = PROMPT_ENGINEERING_AVAILABLE if 'PROMPT_ENGINEERING_AVAILABLE' in globals() else False
        
        # Check Groq availability
        groq_available = False
        groq_agent = None
        groq_model = None
        try:
            groq_agent = get_agent_instance(provider="groq")
            groq_available = groq_agent is not None
            if groq_agent:
                groq_model = groq_agent.model_name
        except Exception as e:
            logger.debug(f"Groq agent not available: {e}")
        
        # Check Gemini availability
        gemini_available = False
        gemini_agent = None
        gemini_model = None
        try:
            gemini_agent = get_agent_instance(provider="gemini")
            gemini_available = gemini_agent is not None
            if gemini_agent:
                gemini_model = gemini_agent.model_name
        except Exception as e:
            logger.debug(f"Gemini agent not available: {e}")
        
        return {
            "available": AGENT_AVAILABLE and (groq_available or gemini_available),
            "embeddings_available": EMBEDDINGS_AVAILABLE,
            "prompt_engineering": prompt_eng_available,
            "providers": {
                "groq": {
                    "available": groq_available,
                    "initialized": groq_agent is not None,
                    "model_name": groq_model or os.getenv("AGENT_MODEL_NAME", "meta-llama/llama-4-maverick-17b-128e-instruct"),
                    "api_key_set": bool(os.getenv("GROQ_API_KEY"))
                },
                "gemini": {
                    "available": gemini_available,
                    "initialized": gemini_agent is not None,
                    "model_name": gemini_model or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"),
                    "api_key_set": bool(os.getenv("GEMINI_API_KEY"))
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        return {
            "available": False,
            "error": str(e)
        }


# ============================================================================
# PHASE 6: System Reports & Testing API
# ============================================================================

@app.get("/api/system/report")
async def get_system_report():
    """Get comprehensive system report from SYSTEM_REPORT.md"""
    try:
        report_file = BASE_DIR / "SYSTEM_REPORT.md"
        if not report_file.exists():
            raise HTTPException(status_code=404, detail="System report not found")
        
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "last_updated": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
            "size_bytes": len(content)
        }
    except Exception as e:
        logger.error(f"Error reading system report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/stats")
async def get_system_stats():
    """Get real-time system statistics"""
    try:
        # Count files
        uploaded_files = len(list((BASE_DIR / "uploaded_files").glob("*.csv"))) if (BASE_DIR / "uploaded_files").exists() else 0
        metadata_files = len(list((BASE_DIR / "uploaded_files" / "metadata").glob("*.json"))) if (BASE_DIR / "uploaded_files" / "metadata").exists() else 0
        
        # Get test results if available
        test_results_file = BASE_DIR / "unified_test_results.json"
        test_stats = None
        if test_results_file.exists():
            with open(test_results_file, 'r') as f:
                test_data = json.load(f)
                test_stats = test_data.get('summary', {})
        
        # Agent status
        agent_status = {
            "groq": {
                "available": _agent_instances.get("groq") is not None,
                "model": _agent_instances["groq"].model_name if _agent_instances.get("groq") else None
            },
            "gemini": {
                "available": _agent_instances.get("gemini") is not None,
                "model": _agent_instances["gemini"].model_name if _agent_instances.get("gemini") else None
            }
        }
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "files": {
                "uploaded": uploaded_files,
                "with_metadata": metadata_files - 1 if metadata_files > 0 else 0
            },
            "agent": agent_status,
            "testing": test_stats,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TestRunRequest(BaseModel):
    provider: Optional[str] = "gemini"

@app.post("/api/testing/run")
async def run_tests(request: TestRunRequest):
    """Run unified test suite"""
    try:
        import subprocess
        
        cmd = [sys.executable, "unified_test_suite.py", request.provider]
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return {
            "success": True,
            "message": "Test suite started",
            "provider": request.provider,
            "process_id": process.pid
        }
    except Exception as e:
        logger.error(f"Error starting tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/testing/results")
async def get_test_results():
    """Get latest test results"""
    try:
        results_file = BASE_DIR / "unified_test_results.json"
        if not results_file.exists():
            return {"success": False, "message": "No test results found"}
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        return {
            "success": True,
            "results": results,
            "last_updated": datetime.fromtimestamp(results_file.stat().st_mtime).isoformat()
        }
    except Exception as e:
        logger.error(f"Error reading test results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA VISUALIZATION ENDPOINTS
# ============================================================================

# Import dynamic visualizer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dynamic_visualizer import DynamicVisualizer

# Initialize dynamic visualizer
dynamic_visualizer = DynamicVisualizer()

@app.get("/api/visualizations/data/all")
async def get_all_visualization_data():
    """Get all data for visualizations - DYNAMIC VERSION"""
    try:
        data_dir = BASE_DIR / "datagenerator" / "generated_data"
        
        # Use dynamic visualizer - works with ANY CSV files
        visualizations = dynamic_visualizer.generate_all_file_visualizations(data_dir)
        
        return {
            "success": True,
            "visualizations": visualizations
        }
    except Exception as e:
        logger.error(f"Error generating visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/logs")
async def get_system_logs(lines: int = 100):
    """Get recent backend logs"""
    try:
        log_file = BASE_DIR / "backend.log"
        if not log_file.exists():
            return {"success": False, "message": "Log file not found"}
        
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "success": True,
            "logs": ''.join(recent_lines),
            "lines_returned": len(recent_lines),
            "total_lines": len(all_lines)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
