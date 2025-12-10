from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import subprocess
import os
import json
import random
import csv
import re
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
# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "")
if ALLOWED_ORIGINS_ENV:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",")]
else:
    # Default: common development ports
    ALLOWED_ORIGINS = [
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # React default
        "http://localhost:5174",  # Vite alternate
        "http://localhost:5175",  # Vite alternate
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]

# In development, be more permissive - allow any localhost origin
if os.getenv("ENVIRONMENT", "development").lower() == "development":
    # Use regex to allow any localhost port for development
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    logger.info("CORS configured for development: allowing all localhost origins")
else:
    # Production: use explicit origins only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    logger.info(f"CORS configured for production with origins: {ALLOWED_ORIGINS}")

# Exception handler for HTTPException (to ensure CORS headers)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    # CORS headers should be added by middleware, but ensure they're present
    origin = request.headers.get("origin")
    if origin:
        # Check if origin is allowed (for development, localhost is allowed)
        if os.getenv("ENVIRONMENT", "development").lower() == "development":
            import re
            if re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?", origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
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

# Phase 3: Semantic Indexing imports (now in backend/)
try:
    from embeddings import Embedder, MongoDBVectorStore, Retriever
    EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Embeddings module not available: {str(e)}")
    EMBEDDINGS_AVAILABLE = False
    Embedder = None
    MongoDBVectorStore = None
    Retriever = None

# Phase 4: LangChain Agent System imports (now in backend/)
try:
    from tools import DataCalculator, TrendAnalyzer, ComparativeAnalyzer, KPICalculator, GraphGenerator
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
    PROMPT_ENGINEERING_AVAILABLE = False  # Removed - no longer in separate directory
    logger.info("✓ Agent modules imported successfully")
except ImportError as e:
    logger.error(f"Agent module not available: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    AGENT_AVAILABLE = False
    PROMPT_ENGINEERING_AVAILABLE = False


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
    """DEPRECATED: Data generator directory removed. Use /api/data-generator/generate instead."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Data generator has been removed. Use /api/data-generator/generate for industry-based data generation."
    )
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


# DEPRECATED: Old endpoint for listing generated files from local directory
# This endpoint is kept for backward compatibility but should not be used in production
# Use /api/files/list instead (MongoDB-based, user-specific)
@app.get("/api/files")
async def list_generated_files():
    """DEPRECATED: List all generated data files with their row counts (local storage)."""
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

class QuestionGenerationRequest(BaseModel):
    """Request model for question generation."""
    file_id: Optional[str] = Field(None, description="File ID to generate questions for (required if generate_all_files is False)")
    table_name: Optional[str] = Field(None, description="Table/Sheet name to generate questions for")
    question_types: Optional[List[str]] = Field(None, description="Types of questions to generate (factual, aggregation, comparative, trend)")
    num_questions: int = Field(10, ge=1, le=100, description="Number of questions to generate per file/table")
    generate_all_files: bool = Field(False, description="Generate questions for all files")


@app.post("/api/question-generator/generate")
async def generate_questions(
    request: QuestionGenerationRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """Generate verified questions for a specific file/table or all files using MongoDB-based question generator."""
    try:
        from services.question_generator_service import MongoDBQuestionGenerator
        from services.file_service import get_user_files
        
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not available - question generator requires MongoDB"
            )
        
        generator = MongoDBQuestionGenerator(current_user)
        all_results = []
        total_generated = 0
        total_failed = 0
        total_verified = 0
        
        if request.generate_all_files:
            # Generate for all files
            files = await get_user_files(current_user, deduplicate=True)
            if not files:
                raise HTTPException(
                    status_code=404,
                    detail="No files found. Please upload files first."
                )
            
            for file_info in files:
                file_id = file_info.get("file_id")
                metadata = file_info.get("metadata", {})
                sheets = metadata.get("sheets", {})
                
                for sheet_name in sheets.keys():
                    result = await generator.generate_questions_for_file(
                        file_id=file_id,
                        table_name=sheet_name,
                        question_types=request.question_types,
                        num_questions=request.num_questions
                    )
                    
                    if result.get("success"):
                        all_results.append({
                            "file_id": file_id,
                            "table_name": sheet_name,
                            "result": result
                        })
                        total_generated += result.get("generated", 0)
                        total_failed += result.get("failed", 0)
                        total_verified += result.get("verified", 0)
        else:
            # Generate for specific file/table
            if not request.file_id:
                raise HTTPException(
                    status_code=400,
                    detail="file_id is required when generate_all_files is False"
                )
            
            if not request.table_name:
                raise HTTPException(
                    status_code=400,
                    detail="table_name is required when generate_all_files is False"
                )
            
            result = await generator.generate_questions_for_file(
                file_id=request.file_id,
                table_name=request.table_name,
                question_types=request.question_types,
                num_questions=request.num_questions
            )
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to generate questions")
                )
            
            all_results.append({
                "file_id": request.file_id,
                "table_name": request.table_name,
                "result": result
            })
            total_generated = result.get("generated", 0)
            total_failed = result.get("failed", 0)
            total_verified = result.get("verified", 0)
        
        return {
            "status": "success",
            "message": f"Generated {total_verified} verified questions ({total_generated} total, {total_failed} failed)",
            "result": {
                "generated": total_generated,
                "failed": total_failed,
                "verified": total_verified,
                "details": all_results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error generating questions: {str(e)}"
        )


@app.post("/api/question-generator/normalize/{file_id}")
async def normalize_file(
    file_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Normalize file data into tables collection for question generation."""
    try:
        from services.question_generator_service import MongoDBQuestionGenerator
        
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not available - question generator requires MongoDB"
            )
        
        generator = MongoDBQuestionGenerator(current_user)
        result = await generator.normalize_file_to_tables(file_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to normalize file")
            )
        
        return {
            "status": "success",
            "message": f"Normalized {result.get('normalized_count', 0)} rows from file",
            "normalized_count": result.get("normalized_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error normalizing file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error normalizing file: {str(e)}"
        )


@app.post("/api/question-generator/verify-all")
async def verify_all_questions(
    current_user: UserInDB = Depends(get_current_user)
):
    """Verify all unverified questions in the QA bank."""
    try:
        from services.question_generator_service import MongoDBQuestionGenerator
        from database import get_database
        
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not available - question generator requires MongoDB"
            )
        
        db = get_database()
        qa_bank_collection = db["qa_bank"]
        tables_collection = db["tables"]
        
        # Get all unverified questions for this user
        unverified_questions = await qa_bank_collection.find({
            "user_id": current_user.id,
            "verified": False
        }).to_list(length=1000)
        
        if not unverified_questions:
            return {
                "success": True,
                "message": "No unverified questions found",
                "verified": 0,
                "still_unverified": 0
            }
        
        verified_count = 0
        still_unverified = 0
        error_details = []
        
        generator = MongoDBQuestionGenerator(current_user)
        
        for q in unverified_questions:
            try:
                file_id = q.get("file_id")
                table_name = q.get("table_name", "Sheet1")
                verification_query = q.get("verification_query", {})
                expected_answer = q.get("answer_structured", {})
                
                if not verification_query:
                    still_unverified += 1
                    continue
                
                # Verify the answer
                is_verified, verification_result = await generator.verify_answer(
                    file_id=file_id,
                    table_name=table_name,
                    verification_query=verification_query,
                    expected_answer=expected_answer,
                    answer_text=q.get("answer_text")
                )
                
                if is_verified:
                    # Update question as verified
                    await qa_bank_collection.update_one(
                        {"_id": q["_id"]},
                        {"$set": {"verified": True, "verification_result": verification_result}}
                    )
                    verified_count += 1
                else:
                    still_unverified += 1
                    error_details.append({
                        "question": q.get("question_text", ""),
                        "expected": str(expected_answer.get("value", "")),
                        "computed": str(verification_result.get("computed_value", "")),
                        "error": verification_result.get("error", "Mismatch")
                    })
            except Exception as e:
                still_unverified += 1
                error_details.append({
                    "question": q.get("question_text", ""),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Verified {verified_count} questions, {still_unverified} still unverified",
            "verified": verified_count,
            "still_unverified": still_unverified,
            "error_details": error_details[:10],  # Limit to first 10 errors
            "tables_count": await tables_collection.count_documents({"user_id": current_user.id})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying questions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error verifying questions: {str(e)}"
        )


@app.get("/api/question-generator/questions")
async def get_questions(
    category: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user)
):
    """Get all verified questions from QA bank for the authenticated user."""
    try:
        from services.question_generator_service import MongoDBQuestionGenerator
        from database import get_database
        
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="MongoDB not available - question generator requires MongoDB"
            )
        
        # Use MongoDBQuestionGenerator to get questions
        generator = MongoDBQuestionGenerator(current_user)
        result = await generator.get_all_questions()
        
        # Calculate verified count
        verified_count = 0
        for difficulty_questions in result.get("questions", {}).values():
            verified_count += sum(1 for q in difficulty_questions if q.get("verified", False))
        
        # Filter by category if provided
        if category:
            category_lower = category.lower()
            filtered_questions = {}
            for diff, questions in result.get("questions", {}).items():
                if category_lower in diff.lower():
                    filtered_questions[diff] = questions
            result["questions"] = filtered_questions
        
        return {
            "success": True,
            "questions": result,
            "total_questions": result.get("metadata", {}).get("total_questions", 0),
            "verified_count": verified_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching questions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching questions: {str(e)}"
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
async def run_benchmark(request: Optional[BenchmarkRequest] = None):
    """Run LLM benchmarking (placeholder - actual execution would run benchmark scripts)."""
    benchmark_dir = BASE_DIR / "backend" / "visualizations" / "llm_benchmarking"
    results_dir = benchmark_dir / "results"
    
    if not results_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Benchmark results directory not found. Please run the benchmark script first."
        )
    
    return {
        "status": "success",
        "message": "Benchmark execution triggered. Results will be available at /api/benchmark/results",
        "output": "Note: This endpoint is a placeholder. Actual benchmark execution should be done via scripts."
    }


@app.get("/api/benchmark/results")
async def get_benchmark_results():
    """Get LLM benchmarking results from the results directory."""
    benchmark_dir = BASE_DIR / "backend" / "visualizations" / "llm_benchmarking"
    results_dir = benchmark_dir / "results"
    metrics_dir = results_dir / "metrics"
    raw_responses_dir = results_dir / "raw_responses"
    
    if not results_dir.exists():
        return {
            "status": "not_found",
            "message": "Benchmark results not found. Please run the benchmark first.",
            "results": None
        }
    
    try:
        # Load summary.json
        summary_file = metrics_dir / "summary.json"
        summary_data = {}
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
        
        # Load all_results.json
        all_results_file = metrics_dir / "all_results.json"
        all_results_data = {}
        if all_results_file.exists():
            with open(all_results_file, 'r') as f:
                all_results_data = json.load(f)
        
        # Load CSV files
        model_comparison_file = results_dir / "model_comparison.csv"
        category_breakdown_file = results_dir / "category_breakdown.csv"
        
        model_comparison = []
        category_breakdown = []
        
        if model_comparison_file.exists():
            with open(model_comparison_file, 'r') as f:
                reader = csv.DictReader(f)
                model_comparison = list(reader)
        
        if category_breakdown_file.exists():
            with open(category_breakdown_file, 'r') as f:
                reader = csv.DictReader(f)
                category_breakdown = list(reader)
        
        # Load raw responses if available
        raw_responses = {}
        if raw_responses_dir.exists():
            for model_dir in raw_responses_dir.iterdir():
                if model_dir.is_dir():
                    results_file = model_dir / "results.json"
                    if results_file.exists():
                        with open(results_file, 'r') as f:
                            raw_responses[model_dir.name] = json.load(f)
        
        # Extract results array from all_results_data
        results_array = []
        if isinstance(all_results_data, dict) and "results" in all_results_data:
            results_array = all_results_data["results"]
        elif isinstance(all_results_data, list):
            results_array = all_results_data
        
        # Load all_results.csv as well for additional data
        all_results_csv = []
        all_results_csv_file = metrics_dir / "all_results.csv"
        if all_results_csv_file.exists():
            with open(all_results_csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                all_results_csv = list(reader)
        
        # Structure response to match frontend expectations
        # Frontend expects either:
        # 1. results.results (array) - from all_results.json
        # 2. results.by_model and results.by_category - from summary.json
        response_data = {
            "status": "success",
            "results": {
                # Include summary data with by_model and by_category for frontend
                "by_model": summary_data.get("by_model", {}),
                "by_category": summary_data.get("by_category", {}),
                "total_evaluations": summary_data.get("total_evaluations", 0),
                "models_evaluated": summary_data.get("models_evaluated", []),
                "categories_evaluated": summary_data.get("categories_evaluated", []),
                # Include results array for frontend processing
                "results": results_array,
                # Include all data for completeness
                "summary": summary_data,
                "all_results": all_results_data,
                "all_results_csv": all_results_csv,
                "model_comparison": model_comparison,
                "category_breakdown": category_breakdown,
                "raw_responses": raw_responses
            },
            # Also include at top level for backward compatibility
            "summary": summary_data,
            "all_results": all_results_data,
            "by_model": summary_data.get("by_model", {}),
            "by_category": summary_data.get("by_category", {})
        }
        
        return response_data
    except Exception as e:
        logger.error(f"Error loading benchmark results: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error loading benchmark results: {str(e)}"
        )


# ============================================================================
# Prompt Engineering Endpoints
# ============================================================================

@app.post("/api/prompt-engineering/test")
async def test_enhanced_prompts():
    """Run prompt engineering test (placeholder - actual execution would run test scripts)."""
    prompt_dir = BASE_DIR / "backend" / "visualizations" / "prompt_engineering"
    results_dir = prompt_dir / "results"
    
    if not results_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Prompt engineering results directory not found. Please run the test script first."
        )
    
    return {
        "status": "success",
        "message": "Prompt engineering test triggered. Results will be available at /api/prompt-engineering/results",
        "output": "Note: This endpoint is a placeholder. Actual test execution should be done via scripts."
    }


@app.get("/api/prompt-engineering/results")
async def get_prompt_results():
    """Get prompt engineering results from the results directory."""
    prompt_dir = BASE_DIR / "backend" / "visualizations" / "prompt_engineering"
    results_dir = prompt_dir / "results"
    
    if not results_dir.exists():
        return {
            "status": "not_found",
            "message": "Prompt engineering results not found. Please run the test first.",
            "results": None
        }
    
    try:
        # Load baseline_vs_enhanced_comparison.json
        comparison_file = results_dir / "baseline_vs_enhanced_comparison.json"
        comparison_data = {}
        if comparison_file.exists():
            with open(comparison_file, 'r') as f:
                comparison_data = json.load(f)
        
        # Load enhanced_prompt_results.json
        enhanced_file = results_dir / "enhanced_prompt_results.json"
        enhanced_data = {}
        if enhanced_file.exists():
            with open(enhanced_file, 'r') as f:
                enhanced_data = json.load(f)
        
        # Load CSV file
        csv_file = results_dir / "baseline_vs_enhanced_comparison.csv"
        csv_data = []
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
        
        # Extract report and detailed_results from comparison_data
        report = comparison_data.get("report", {})
        detailed_results = comparison_data.get("detailed_results", [])
        
        return {
            "status": "success",
            "report": report,
            "detailed_results": detailed_results,
            "enhanced_results": enhanced_data,
            "csv_data": csv_data,
            "results": comparison_data  # Include full data for backward compatibility
        }
    except Exception as e:
        logger.error(f"Error loading prompt engineering results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading prompt engineering results: {str(e)}"
        )


# ============================================================================
# Comparison Analysis Endpoints
# ============================================================================

@app.post("/api/comparison/run")
async def run_comparison():
    """Run comparison analysis (placeholder - actual execution would run comparison scripts)."""
    comparison_dir = BASE_DIR / "backend" / "visualizations" / "enhanced_vs_baseline_vs_groundtruth"
    results_dir = comparison_dir / "results"
    
    if not results_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Comparison results directory not found. Please run the comparison script first."
        )
    
    return {
        "status": "success",
        "message": "Comparison analysis triggered. Results will be available at /api/comparison/results",
        "output": "Note: This endpoint is a placeholder. Actual comparison execution should be done via scripts."
    }


@app.get("/api/comparison/results")
async def get_comparison_results():
    """Get comparison analysis results from the results directory."""
    comparison_dir = BASE_DIR / "backend" / "visualizations" / "enhanced_vs_baseline_vs_groundtruth"
    results_dir = comparison_dir / "results"
    
    if not results_dir.exists():
        return {
            "status": "not_found",
            "message": "Comparison results not found. Please run the comparison first.",
            "results": None
        }
    
    try:
        # Load three_way_comparison.json
        comparison_file = results_dir / "three_way_comparison.json"
        comparison_data = {}
        if comparison_file.exists():
            with open(comparison_file, 'r') as f:
                comparison_data = json.load(f)
        
        # Load CSV file
        csv_file = results_dir / "three_way_comparison.csv"
        csv_data = []
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
        
        # Load comparison report text
        report_file = results_dir / "comparison_report.txt"
        report_text = ""
        if report_file.exists():
            with open(report_file, 'r') as f:
                report_text = f.read()
        
        # Extract report and detailed_results from comparison_data
        report = comparison_data.get("report", {})
        detailed_results = comparison_data.get("detailed_results", [])
        
        return {
            "status": "success",
            "report": report,
            "detailed_results": detailed_results,
            "report_text": report_text,
            "csv_data": csv_data,
            "results": comparison_data  # Include full data for backward compatibility
        }
    except Exception as e:
        logger.error(f"Error loading comparison results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading comparison results: {str(e)}"
        )


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
        "message": "Visualization endpoints are active"
    }


@app.get("/api/visualizations/benchmark/list")
async def list_benchmark_visualizations():
    """List all benchmark visualization images."""
    benchmark_dir = BASE_DIR / "backend" / "visualizations" / "llm_benchmarking"
    viz_dir = benchmark_dir / "results" / "visualizations"
    
    if not viz_dir.exists():
        return {
            "status": "not_found",
            "images": [],
            "message": "Visualization directory not found"
        }
    
    try:
        # Get all PNG files
        image_files = list(viz_dir.glob("*.png"))
        images = []
        
        for img_file in sorted(image_files):
            images.append({
                "name": img_file.name,
                "url": f"/api/visualizations/benchmark/{img_file.name}",
                "size": img_file.stat().st_size,
                "modified": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "images": images,
            "count": len(images)
        }
    except Exception as e:
        logger.error(f"Error listing benchmark visualizations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing benchmark visualizations: {str(e)}"
        )


@app.get("/api/visualizations/prompt-engineering/list")
async def list_prompt_visualizations():
    """List all prompt engineering visualization images."""
    prompt_dir = BASE_DIR / "backend" / "visualizations" / "prompt_engineering"
    viz_dir = prompt_dir / "results" / "visualizations"
    
    if not viz_dir.exists():
        return {
            "status": "not_found",
            "images": [],
            "message": "Visualization directory not found"
        }
    
    try:
        # Get all PNG files
        image_files = list(viz_dir.glob("*.png"))
        images = []
        
        for img_file in sorted(image_files):
            images.append({
                "name": img_file.name,
                "url": f"/api/visualizations/prompt-engineering/{img_file.name}",
                "size": img_file.stat().st_size,
                "modified": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "images": images,
            "count": len(images)
        }
    except Exception as e:
        logger.error(f"Error listing prompt engineering visualizations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing prompt engineering visualizations: {str(e)}"
        )


@app.get("/api/visualizations/comparison/list")
async def list_comparison_visualizations():
    """List all comparison visualization images."""
    comparison_dir = BASE_DIR / "backend" / "visualizations" / "enhanced_vs_baseline_vs_groundtruth"
    viz_dir = comparison_dir / "results" / "visualizations"
    
    if not viz_dir.exists():
        return {
            "status": "not_found",
            "images": [],
            "message": "Visualization directory not found"
        }
    
    try:
        # Get all PNG files
        image_files = list(viz_dir.glob("*.png"))
        images = []
        
        for img_file in sorted(image_files):
            images.append({
                "name": img_file.name,
                "url": f"/api/visualizations/comparison/{img_file.name}",
                "size": img_file.stat().st_size,
                "modified": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "images": images,
            "count": len(images)
        }
    except Exception as e:
        logger.error(f"Error listing comparison visualizations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing comparison visualizations: {str(e)}"
        )


@app.get("/api/visualizations/benchmark/{image_name}")
async def get_benchmark_visualization(image_name: str):
    """Get a specific benchmark visualization image."""
    benchmark_dir = BASE_DIR / "backend" / "visualizations" / "llm_benchmarking"
    viz_dir = benchmark_dir / "results" / "visualizations"
    image_path = viz_dir / image_name
    
    # Security: prevent directory traversal
    if ".." in image_name or not image_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_name
    )


@app.get("/api/visualizations/prompt-engineering/{image_name}")
async def get_prompt_visualization(image_name: str):
    """Get a specific prompt engineering visualization image."""
    prompt_dir = BASE_DIR / "backend" / "visualizations" / "prompt_engineering"
    viz_dir = prompt_dir / "results" / "visualizations"
    image_path = viz_dir / image_name
    
    # Security: prevent directory traversal
    if ".." in image_name or not image_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_name
    )


@app.get("/api/visualizations/comparison/{image_name}")
async def get_comparison_visualization(image_name: str):
    """Get a specific comparison visualization image."""
    comparison_dir = BASE_DIR / "backend" / "visualizations" / "enhanced_vs_baseline_vs_groundtruth"
    viz_dir = comparison_dir / "results" / "visualizations"
    image_path = viz_dir / image_name
    
    # Security: prevent directory traversal
    if ".." in image_name or not image_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=image_name
    )


# ============================================================================
# Phase 1: Excel Parser API Endpoints
# ============================================================================

# Import Excel Parser modules (now in backend/)
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

# Phase 3: Semantic Indexing setup - Now using MongoDB instead of local ChromaDB
# No local vector store directory needed - everything in MongoDB

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
    """Get or create MongoDB vector store instance."""
    global _vector_store
    if not EMBEDDINGS_AVAILABLE:
        return None
    if not MONGODB_AVAILABLE:
        logger.warning("MongoDB not available - vector store requires MongoDB")
        return None
    if _vector_store is None:
        try:
            from database import get_database
            database = get_database()
            _vector_store = MongoDBVectorStore(database=database, collection_name="embeddings")
            logger.info("✓ MongoDB vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB vector store: {str(e)}")
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


if MONGODB_AVAILABLE:
    @app.post("/api/files/upload")
    async def upload_file(
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user)
    ):
        """
        Upload an Excel or CSV file (requires authentication).
        Files are stored in MongoDB GridFS with user context.
        
        Returns:
            File ID and basic metadata
        """
        try:
            if not file.filename:
                raise HTTPException(status_code=400, detail="Filename is required")
            
            logger.info(f"Starting file upload: {file.filename} for user {current_user.id}")
            
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ['.xlsx', '.xls', '.csv']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {file_ext}. Supported: .xlsx, .xls, .csv"
                )
            
            # Check for duplicate filename before processing
            from services.file_service import get_user_files
            existing_files = await get_user_files(current_user)
            duplicate_file = next(
                (f for f in existing_files if f.get("original_filename") == file.filename),
                None
            )
            if duplicate_file:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": f"File '{file.filename}' already exists",
                        "existing_file_id": duplicate_file.get("file_id"),
                        "existing_file": duplicate_file
                    }
                )
            
            # Read file content
            file_content = await file.read()
            if len(file_content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
            # Save to temporary file for validation and metadata extraction
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = Path(tmp_file.name)
            
            try:
                # Validate file
                validation_result = file_validator.validate_file(tmp_file_path)
                if not validation_result['is_valid']:
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
                    metadata = metadata_extractor.extract_metadata(tmp_file_path, include_sample=True)
                    if isinstance(metadata, dict) and 'error' in metadata:
                        logger.warning(f"Metadata extraction returned error: {metadata.get('error')}")
                except Exception as e:
                    logger.error(f"Error extracting metadata: {str(e)}")
                    metadata = {
                        'error': f"Error extracting metadata: {str(e)}",
                        'file_name': file.filename,
                        'file_type': file_ext.replace('.', ''),
                        'file_size_bytes': len(file_content),
                        'sheet_names': [],
                        'sheets': {}
                    }
                
                # Import file service
                from services.file_service import upload_file_to_gridfs
                
                # Upload to MongoDB GridFS
                result = await upload_file_to_gridfs(
                    user=current_user,
                    file_content=file_content,
                    original_filename=file.filename,
                    file_metadata=metadata,
                    industry=current_user.industry
                )
                
                logger.info(f"File upload successful: {result['file_id']} ({file.filename})")
                
                return {
                    "success": True,
                    "file_id": result["file_id"],
                    "original_filename": result["original_filename"],
                    "uploaded_at": result["uploaded_at"],
                    "file_size_bytes": result["file_size_bytes"],
                    "metadata": metadata,
                    "warnings": validation_result.get('warnings', [])
                }
            
            finally:
                # Clean up temporary file
                if tmp_file_path.exists():
                    tmp_file_path.unlink()
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Error uploading file",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )


    @app.get("/api/files/list")
    async def list_uploaded_files(current_user: UserInDB = Depends(get_current_user)):
        """
        List all uploaded files for the current user (requires authentication).
        
        This endpoint returns files from MongoDB GridFS, filtered by user_id.
        """
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="File service not available - MongoDB not configured"
            )
        
        try:
            from services.file_service import get_user_files
            import math
            
            logger.info(f"Listing files for user: {current_user.id} (email: {current_user.email})")
            # Deduplicate by default - only show most recent file for each filename
            files = await get_user_files(current_user, deduplicate=True)
            
            # Sanitize files to remove any invalid float values (inf, nan)
            def sanitize_value(value):
                """Recursively sanitize values for JSON serialization"""
                if isinstance(value, float):
                    if math.isnan(value) or math.isinf(value):
                        return None
                elif isinstance(value, dict):
                    return {k: sanitize_value(v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [sanitize_value(item) for item in value]
                return value
            
            sanitized_files = [sanitize_value(f) for f in files]
            
            logger.info(f"Successfully listed {len(sanitized_files)} files for user {current_user.id}")
            
            return {
                "success": True,
                "files": sanitized_files,
                "total": len(sanitized_files),
                "deduplicated": True
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error listing files: {str(e)}"
            )


    @app.get("/api/files/{file_id}")
    async def get_file_info(
        file_id: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get detailed information about an uploaded file (requires authentication)."""
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="File service not available - MongoDB not configured"
            )
        
        try:
            from services.file_service import get_file_metadata
            file_info = await get_file_metadata(file_id, current_user)
            
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Extract user_definitions from metadata for backward compatibility
            user_definitions = file_info.get("metadata", {}).get("user_definitions", {})
            
            return {
                "success": True,
                **file_info,
                "user_definitions": user_definitions  # Add at top level for backward compatibility
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/files/{file_id}/columns")
    async def get_file_columns(
        file_id: str,
        sheet_name: Optional[str] = None,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get columns for a file (and optionally a specific sheet) - requires authentication."""
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="File service not available - MongoDB not configured"
            )
        
        try:
            from services.file_service import get_file_metadata, get_file_from_gridfs
            import pandas as pd
            import io
            
            # Get file metadata (user-specific)
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get file content from GridFS
            file_content = await get_file_from_gridfs(file_id, current_user)
            if not file_content:
                raise HTTPException(status_code=404, detail="File content not found")
            
            # Get user definitions from metadata
            user_definitions = file_info.get("metadata", {}).get("user_definitions", {})
            
            # Load file into pandas
            file_ext = Path(file_info["original_filename"]).suffix.lower()
            
            if file_ext == '.csv':
                # CSV files have a single sheet
                df = pd.read_csv(io.BytesIO(file_content))
                sheet_name_actual = "Sheet1"
                
                # Build column objects with metadata
                columns = []
                for col in df.columns:
                    col_key = f"{sheet_name_actual}::{col}"
                    columns.append({
                        "name": col,
                        "sheet": sheet_name_actual,
                        "type": str(df[col].dtype),
                        "null_count": int(df[col].isna().sum()),
                        "unique_count": int(df[col].nunique()),
                        "user_definition": user_definitions.get(col_key, "")
                    })
                
                return {
                    "file_id": file_id,
                    "columns": {
                        sheet_name_actual: columns
                    }
                }
            else:
                # Excel files can have multiple sheets
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                all_columns = {}
                
                if sheet_name:
                    # Return columns for specific sheet
                    if sheet_name not in excel_file.sheet_names:
                        raise HTTPException(status_code=404, detail=f"Sheet '{sheet_name}' not found")
                    
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    columns = []
                    for col in df.columns:
                        col_key = f"{sheet_name}::{col}"
                        columns.append({
                            "name": col,
                            "sheet": sheet_name,
                            "type": str(df[col].dtype),
                            "null_count": int(df[col].isna().sum()),
                            "unique_count": int(df[col].nunique()),
                            "user_definition": user_definitions.get(col_key, "")
                        })
                    all_columns[sheet_name] = columns
                    
                    return {
                        "file_id": file_id,
                        "sheet_name": sheet_name,
                        "columns": all_columns
                    }
                else:
                    # Return columns for all sheets
                    for sheet_name_actual in excel_file.sheet_names:
                        df = pd.read_excel(excel_file, sheet_name=sheet_name_actual)
                        columns = []
                        for col in df.columns:
                            col_key = f"{sheet_name_actual}::{col}"
                            columns.append({
                                "name": col,
                                "sheet": sheet_name_actual,
                                "type": str(df[col].dtype),
                                "null_count": int(df[col].isna().sum()),
                                "unique_count": int(df[col].nunique()),
                                "user_definition": user_definitions.get(col_key, "")
                            })
                        all_columns[sheet_name_actual] = columns
                    
                    return {
                        "file_id": file_id,
                        "columns": all_columns
                    }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file columns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    


    @app.post("/api/files/{file_id}/definitions")
    async def save_column_definitions(
        file_id: str,
        definitions: Dict[str, str],
        current_user: UserInDB = Depends(get_current_user)
    ):
        """
        Save user definitions for columns (requires authentication).
        
        Request body:
        {
            "Sheet1::column_name": "User definition text",
            "Sheet2::column_name": "Another definition"
        }
        """
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="File service not available - MongoDB not configured"
            )
        
        try:
            from database import get_database
            db = get_database()
            files_collection = db["files"]
            
            # Find file (must belong to user)
            file_doc = await files_collection.find_one({
                "file_id": file_id,
                "user_id": current_user.id
            })
            
            if not file_doc:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get current metadata or initialize it
            metadata = file_doc.get("metadata", {})
            
            # Initialize user_definitions if it doesn't exist
            if "user_definitions" not in metadata:
                metadata["user_definitions"] = {}
            
            # Merge new definitions with existing ones
            metadata["user_definitions"].update(definitions)
            
            # Update in database using dot notation to ensure nested field is set correctly
            await files_collection.update_one(
                {"_id": file_doc["_id"]},
                {"$set": {"metadata.user_definitions": metadata["user_definitions"]}}
            )
            
            logger.info(f"Updated user_definitions for file {file_id}: {len(metadata['user_definitions'])} definitions")
            
            return {
                "success": True,
                "message": "Column definitions saved successfully",
                "definitions_count": len(file_doc["metadata"]["user_definitions"])
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving definitions: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.delete("/api/files/{file_id}")
    async def delete_file(
        file_id: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Delete an uploaded file and its metadata (requires authentication)."""
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="File service not available - MongoDB not configured"
            )
        
        try:
            from services.file_service import delete_file as delete_file_service
            success = await delete_file_service(file_id, current_user)
            
            if not success:
                raise HTTPException(status_code=404, detail="File not found")
            
            return {
                "success": True,
                "message": f"File {file_id} deleted successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


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

if MONGODB_AVAILABLE:
    @app.get("/api/column-definitions")
    async def get_all_column_definitions(current_user: UserInDB = Depends(get_current_user)):
        """Get all column definitions across all files for the current user."""
        try:
            from database import get_database
            db = get_database()
            files_collection = db["files"]
            
            all_definitions = {}
            
            # Find all files for user
            cursor = files_collection.find({"user_id": current_user.id})
            async for doc in cursor:
                file_id = doc["file_id"]
                metadata = doc.get("metadata", {})
                user_defs = metadata.get("user_definitions", {})
                
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
    async def save_column_definition(
        definition_data: Dict[str, Any],
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Save or update a column definition (requires authentication)."""
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Service not available - MongoDB not configured"
            )
        
        try:
            from database import get_database
            db = get_database()
            files_collection = db["files"]
            
            file_id = definition_data.get("file_id")
            column_key = definition_data.get("column_key")
            definition = definition_data.get("definition", "")
            
            if not file_id or not column_key:
                raise HTTPException(status_code=400, detail="file_id and column_key are required")
            
            # Find file (must belong to user)
            file_doc = await files_collection.find_one({
                "file_id": file_id,
                "user_id": current_user.id
            })
            
            if not file_doc:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get current metadata or initialize it
            metadata = file_doc.get("metadata", {})
            
            # Initialize user_definitions if it doesn't exist
            if "user_definitions" not in metadata:
                metadata["user_definitions"] = {}
            
            # Set the definition
            metadata["user_definitions"][column_key] = definition
            
            # Update in database using dot notation to ensure nested field is set correctly
            await files_collection.update_one(
                {"_id": file_doc["_id"]},
                {"$set": {"metadata.user_definitions": metadata["user_definitions"]}}
            )
            
            logger.info(f"Saved definition for {file_id}::{column_key}")
            
            return {"success": True, "message": "Definition saved"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving column definition: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/column-definitions/{file_id}/{column_key:path}")
    async def delete_column_definition(
        file_id: str,
        column_key: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Delete a column definition (requires authentication)."""
        if not MONGODB_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Service not available - MongoDB not configured"
            )
        
        try:
            from database import get_database
            db = get_database()
            files_collection = db["files"]
            
            # Find file (must belong to user)
            file_doc = await files_collection.find_one({
                "file_id": file_id,
                "user_id": current_user.id
            })
            
            if not file_doc:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get user definitions
            metadata = file_doc.get("metadata", {})
            user_defs = metadata.get("user_definitions", {})
            
            if column_key in user_defs:
                del user_defs[column_key]
                
                # Update in database using dot notation
                await files_collection.update_one(
                    {"_id": file_doc["_id"]},
                    {"$set": {"metadata.user_definitions": user_defs}}
                )
                
                logger.info(f"Deleted definition for {file_id}::{column_key}")
                return {"success": True, "message": "Definition deleted"}
            else:
                return {"success": True, "message": "Definition not found (already deleted)"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting column definition: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

if MONGODB_AVAILABLE:
    @app.post("/api/relationships/analyze-all")
    async def analyze_all_relationships(current_user: UserInDB = Depends(get_current_user)):
        """
        Analyze relationships across ALL files at once (requires authentication).
        Uses Gemini with all column definitions and metadata.
        Results are cached and updated only when needed.
        """
        try:
            from database import get_database
            db = get_database()
            files_collection = db["files"]
            
            logger.info(f"Starting batch relationship analysis for user {current_user.id}...")
            
            # Collect all files and their metadata for the user
            all_files_data = []
            all_column_definitions = {}
            
            # Find all files for user
            cursor = files_collection.find({"user_id": current_user.id})
            async for doc in cursor:
                file_id = doc["file_id"]
                
                # Get columns for this file (extract directly from metadata)
                try:
                    metadata = doc.get("metadata", {})
                    sheets = metadata.get("sheets", {})
                    user_defs = metadata.get("user_definitions", {})
                    
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
                        "filename": doc.get("original_filename", "unknown"),
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
            
            # Check cache in MongoDB
            from database import get_database
            db = get_database()
            cache_collection = db["relationship_cache"]
            
            # Calculate current file IDs (needed for cache check and later for saving)
            current_file_ids = set([f["file_id"] for f in all_files_data])
            
            # Find cache for this user
            cache_doc = await cache_collection.find_one({"user_id": current_user.id})
            
            if cache_doc:
                cached_file_ids = set(cache_doc.get("file_ids", []))
                
                if cached_file_ids == current_file_ids and cache_doc.get("all_files_relationships"):
                    logger.info("Using cached relationship analysis from MongoDB")
                    analyzed_at = cache_doc.get("analyzed_at", "")
                    return {
                        "success": True,
                        "message": f"Using cached results from MongoDB (analyzed at {analyzed_at})",
                        "relationships": cache_doc.get("all_files_relationships", []),
                        "cached": True,
                        "analyzed_at": analyzed_at,
                        "file_count": len(all_files_data),
                        "note": "Cache is stored in MongoDB relationship_cache collection, not local storage"
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
                    
                    # Get sample data for context (first few rows from each file) - from GridFS
                    sample_data = []
                    from services.file_service import get_file_from_gridfs
                    import pandas as pd
                    import io
                    
                    for file_data in all_files_data[:5]:  # Limit to first 5 files for context
                        try:
                            # Get file content from GridFS
                            file_content = await get_file_from_gridfs(file_data["file_id"], current_user)
                            if file_content:
                                file_ext = Path(file_data["filename"]).suffix.lower()
                                if file_ext == '.csv':
                                    df = pd.read_csv(io.BytesIO(file_content))
                                else:
                                    df = pd.read_excel(io.BytesIO(file_content))  # Reads first sheet by default
                                
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
            from services.file_service import get_file_from_gridfs
            import pandas as pd
            import io
            
            for file_data in all_files_data:
                try:
                    # Get file content from GridFS
                    file_content = await get_file_from_gridfs(file_data["file_id"], current_user)
                    if file_content:
                        file_ext = Path(file_data["filename"]).suffix.lower()
                        
                        try:
                            # Load file into pandas for basic statistical analysis
                            # Note: We skip full schema detection here since it requires local file paths
                            # Gemini AI analysis above is the primary method anyway
                            if file_ext == '.csv':
                                df = pd.read_csv(io.BytesIO(file_content))
                                # Simple pattern: check for common column names across files
                                # This is a simplified statistical check - Gemini handles the complex analysis
                                for col in df.columns:
                                    # Check if this column name appears in other files (potential foreign key)
                                    for other_file in all_files_data:
                                        if other_file["file_id"] != file_data["file_id"]:
                                            other_metadata = other_file.get("metadata", {})
                                            other_sheets = other_metadata.get("sheets", {})
                                            for other_sheet_name, other_sheet_data in other_sheets.items():
                                                if col in other_sheet_data.get("columns", []):
                                                    statistical_relationships.append({
                                                        "source_column": f"{file_data['filename']}::Sheet1::{col}",
                                                        "target_column": f"{other_file['filename']}::{other_sheet_name}::{col}",
                                                        "type": "potential_foreign_key",
                                                        "file_id": file_data["file_id"],
                                                        "file_name": file_data["filename"],
                                                        "sheet": "Sheet1",
                                                        "source": "statistical_pattern",
                                                        "priority": "medium",
                                                        "confidence": 0.5,
                                                        "strength": "weak",
                                                        "impact": "informational"
                                                    })
                            else:
                                # Excel file - read all sheets
                                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                                for sheet_name in excel_file.sheet_names:
                                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)
                                    if df is not None and not df.empty:
                                        for col in df.columns:
                                            # Check if this column name appears in other files
                                            for other_file in all_files_data:
                                                if other_file["file_id"] != file_data["file_id"]:
                                                    other_metadata = other_file.get("metadata", {})
                                                    other_sheets = other_metadata.get("sheets", {})
                                                    for other_sheet_name, other_sheet_data in other_sheets.items():
                                                        if col in other_sheet_data.get("columns", []):
                                                            statistical_relationships.append({
                                                                "source_column": f"{file_data['filename']}::{sheet_name}::{col}",
                                                                "target_column": f"{other_file['filename']}::{other_sheet_name}::{col}",
                                                                "type": "potential_foreign_key",
                                                                "file_id": file_data["file_id"],
                                                                "file_name": file_data["filename"],
                                                                "sheet": sheet_name,
                                                                "source": "statistical_pattern",
                                                                "priority": "medium",
                                                                "confidence": 0.5,
                                                                "strength": "weak",
                                                                "impact": "informational"
                                                            })
                        except Exception as e:
                            logger.debug(f"Error processing file {file_data['filename']} for statistical analysis: {str(e)}")
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
            
            # Save to cache in MongoDB
            cache_data = {
                "user_id": current_user.id,
                "file_ids": list(current_file_ids),
                "analyzed_at": datetime.now().isoformat(),
                "all_files_relationships": relationships,
                "file_count": len(all_files_data)
            }
            
            # Upsert cache for this user
            await cache_collection.update_one(
                {"user_id": current_user.id},
                {"$set": cache_data},
                upsert=True
            )
            
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

if MONGODB_AVAILABLE:
    @app.post("/api/visualizations/cross-file")
    async def generate_cross_file_visualizations(
        file_ids: List[str],
        current_user: UserInDB = Depends(get_current_user)
    ):
        """
        Generate cross-file relationship visualizations for selected files
        Uses Gemini API and existing relationship data stored in MongoDB (not local cache)
        """
        try:
            from database import get_database
            from services.file_service import get_file_metadata
            from cross_file_visualizer import CrossFileVisualizer
            
            db = get_database()
            cache_collection = db["relationship_cache"]
            
            # Get relationships from MongoDB (this is NOT local storage - it's MongoDB)
            cache_doc = await cache_collection.find_one({"user_id": current_user.id})
            if not cache_doc:
                raise HTTPException(
                    status_code=400,
                    detail="No relationship analysis found. Please run 'Analyze All Relationships' first from the File Upload page."
                )
            
            relationships = cache_doc.get("all_files_relationships", [])
            
            # Get file metadata for selected files and create filename->file_id mapping
            file_metadata = {}
            filename_to_fileid = {}  # Map filename to file_id
            
            for file_id in file_ids:
                metadata = await get_file_metadata(file_id, current_user)
                if metadata:
                    file_metadata[file_id] = metadata
                    filename = metadata.get("original_filename", "")
                    if filename:
                        filename_to_fileid[filename] = file_id
                        # Also map without extension
                        filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        filename_to_fileid[filename_no_ext] = file_id
            
            if not file_metadata:
                raise HTTPException(status_code=404, detail="No valid files found")
            
            # Generate visualizations with filename mapping
            visualizer = CrossFileVisualizer()
            viz_data = await visualizer.generate_cross_file_visualizations(
                relationships=relationships,
                file_ids=file_ids,
                file_metadata=file_metadata,
                filename_to_fileid=filename_to_fileid
            )
            
            return {
                "success": True,
                "visualization": viz_data
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating cross-file visualizations: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/relationships/cached")
    async def get_cached_relationships(current_user: UserInDB = Depends(get_current_user)):
        """Get cached relationship analysis results (requires authentication)."""
        try:
            from database import get_database
            db = get_database()
            cache_collection = db["relationship_cache"]
            
            # Find cache for this user
            cache_doc = await cache_collection.find_one({"user_id": current_user.id})
            
            if cache_doc:
                return {
                    "success": True,
                    "relationships": cache_doc.get("all_files_relationships", []),
                    "analyzed_at": cache_doc.get("analyzed_at"),
                    "file_count": cache_doc.get("file_count", 0),
                    "cached": True
                }
            else:
                return {
                    "success": True,
                    "relationships": [],
                    "analyzed_at": None,
                    "file_count": 0,
                    "cached": False
                }
        except Exception as e:
            logger.error(f"Error getting cached relationships: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/relationships/cache")
    async def clear_relationship_cache(current_user: UserInDB = Depends(get_current_user)):
        """Clear relationship analysis cache for current user (forces re-analysis)."""
        try:
            from database import get_database
            db = get_database()
            cache_collection = db["relationship_cache"]
            
            # Delete cache for this user
            result = await cache_collection.delete_one({"user_id": current_user.id})
            
            if result.deleted_count > 0:
                return {"success": True, "message": "Cache cleared"}
            else:
                return {"success": True, "message": "Cache was already empty"}
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA GENERATOR ENDPOINTS (Industry-based, MongoDB-integrated)
# ============================================================================

if MONGODB_AVAILABLE:
    @app.get("/api/data-generator/schema-preview")
    async def get_schema_preview(
        use_ai: bool = True,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """
        Get schema templates (files and columns) for user's industry (requires authentication).
        
        Args:
            use_ai: Whether to use AI to generate dynamic schema templates (default: True)
        """
        try:
            from services.data_generator_service import get_industry_schema_preview
            
            result = await get_industry_schema_preview(current_user.industry, use_ai=use_ai)
            if not result.get("success"):
                raise HTTPException(status_code=404, detail=result.get("error", "Industry not found"))
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting schema preview: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/data-generator/existing-files")
    async def get_existing_files_for_generator(current_user: UserInDB = Depends(get_current_user)):
        """Get existing files for the user (requires authentication)."""
        try:
            from services.data_generator_service import check_existing_user_files
            
            result = await check_existing_user_files(current_user)
            return result
        except Exception as e:
            logger.error(f"Error getting existing files: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/data-generator/generate")
    async def generate_industry_data(
        rows_per_file: Dict[str, int] = None,
        add_to_existing: bool = False,
        generate_for_existing_sheets: Optional[Dict[str, Dict[str, int]]] = None,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """
        Generate data based on user's industry schema templates and upload to MongoDB (requires authentication).
        
        Args:
            rows_per_file: Dictionary mapping file names (from schema templates) to number of rows
            add_to_existing: Whether to add to existing files or create new ones
            generate_for_existing_sheets: Optional dict mapping file_id -> {sheet_name: num_rows}
                                          to generate data for existing sheets
        """
        try:
            from services.data_generator_service import generate_data_for_industry
            
            if rows_per_file is None:
                rows_per_file = {}
            
            result = await generate_data_for_industry(
                user=current_user,
                industry_name=current_user.industry,
                rows_per_file=rows_per_file,
                add_to_existing=add_to_existing,
                generate_for_existing_sheets=generate_for_existing_sheets
            )
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Data generation failed"))
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
# ============================================
# Phase 3: Semantic Indexing & RAG Endpoints
# ===========================================

async def index_file_in_vector_store(
    file_id: str, 
    file_info: Dict[str, Any], 
    user_id: str,
    current_user: Optional[Any] = None
) -> bool:
    """
    Index a file's columns and metadata into the vector store using full excel_parser capabilities.
    
    This function:
    1. Reads file content from MongoDB GridFS
    2. Uses schema detection results (if available) or triggers schema detection
    3. Incorporates user-provided column definitions
    4. Includes Gemini semantic analysis results
    5. Indexes relationship information with user_id
    
    Args:
        file_id: File ID
        file_info: File information dictionary (from MongoDB)
        user_id: User ID for multi-tenant support
        current_user: Optional UserInDB object for GridFS access
        
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
        # Get user_definitions from MongoDB metadata structure
        metadata = file_info.get("metadata", {})
        user_definitions = metadata.get("user_definitions", {})
        
        # Get file content from MongoDB GridFS
        file_content = None
        if current_user and MONGODB_AVAILABLE:
            try:
                from services.file_service import get_file_from_gridfs
                file_content = await get_file_from_gridfs(file_id, current_user)
            except Exception as e:
                logger.warning(f"Could not load file from GridFS: {str(e)}")
        
        # If GridFS fails, try local path as fallback (for backward compatibility)
        saved_path = file_info.get("saved_path")
        if not file_content and saved_path and Path(saved_path).exists():
            # Fallback to local file (for migration period)
            with open(saved_path, 'rb') as f:
                file_content = f.read()
        
        # Check if we have file content to process
        schema_result = None
        if file_content:
            try:
                import pandas as pd
                import io
                import tempfile
                
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
                
                # Create temporary file for schema detection
                file_ext = Path(file_name).suffix.lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file_path = Path(tmp_file.name)
                
                try:
                    # Run schema detection with user definitions
                    schema_result = schema_detector.detect_schema(
                        file_path=tmp_file_path,
                        user_definitions=schema_user_defs if schema_user_defs else None
                    )
                    
                    # Enhance with Gemini if available
                    if gemini_analyzer and gemini_analyzer.enabled:
                        try:
                            # Load sample data for Gemini from file_content
                            if file_ext in ['.xlsx', '.xls']:
                                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                                dfs = {sheet: pd.read_excel(excel_file, sheet_name=sheet, nrows=100) 
                                       for sheet in excel_file.sheet_names}
                                excel_file.close()
                            else:
                                dfs = {'Sheet1': pd.read_csv(io.BytesIO(file_content), nrows=100)}
                            
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
                finally:
                    # Clean up temporary file
                    if tmp_file_path.exists():
                        tmp_file_path.unlink()
            except Exception as file_error:
                logger.warning(f"Could not process file content: {str(file_error)}")
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
                    
                    # Add to vector store with user_id (async for MongoDB)
                    await vector_store.add_column(
                        file_id=file_id,
                        file_name=file_name,
                        sheet_name=sheet_name,
                        column_name=column_name,
                        embedding=col_metadata["context_embedding"],
                        metadata=col_metadata,
                        user_id=user_id
                    )
                    indexed_count += 1
                
                # Index relationships for this sheet
                relationships = sheet_schema.get('relationships', [])
                for rel in relationships:
                    try:
                        rel_embedding_data = embedder.embed_relationship(rel)
                        await vector_store.add_relationship(
                            relationship=rel,
                            embedding=rel_embedding_data["embedding"],
                            user_id=user_id
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
                    
                    # Add to vector store with user_id (async for MongoDB)
                    await vector_store.add_column(
                        file_id=file_id,
                        file_name=file_name,
                        sheet_name=sheet_name,
                        column_name=column_name,
                        embedding=col_metadata["context_embedding"],
                        metadata=col_metadata,
                        user_id=user_id
                    )
                    indexed_count += 1
            
            logger.info(f"Indexed {indexed_count} columns (basic metadata) for file: {file_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error indexing file {file_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if MONGODB_AVAILABLE:
    @app.post("/api/semantic/index/{file_id}")
    async def index_file(
        file_id: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Index a file into the semantic vector store (requires authentication)."""
        if not EMBEDDINGS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Semantic indexing not available - embeddings not initialized"
            )
        
        try:
            # Get file info from MongoDB
            from services.file_service import get_file_metadata
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail=f"File {file_id} not found")
            
            success = await index_file_in_vector_store(file_id, file_info, current_user.id, current_user)
            
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
    async def index_all_files(current_user: UserInDB = Depends(get_current_user)):
        """Index all uploaded files into the semantic vector store (requires authentication)."""
        if not EMBEDDINGS_AVAILABLE:
            return {
                "success": False,
                "message": "Embeddings module not available",
                "indexed": 0,
                "total": 0
            }
        
        try:
            # Get all files for this user from MongoDB
            from services.file_service import get_user_files
            files = await get_user_files(current_user)
            
            indexed_count = 0
            failed_count = 0
            
            for file_info in files:
                file_id = file_info.get("file_id")
                if file_id:
                    success = await index_file_in_vector_store(file_id, file_info, current_user.id, current_user)
                    if success:
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
        file_id: Optional[str] = Query(None, description="Filter by file ID"),
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Perform semantic search over indexed Excel data (requires authentication)."""
        try:
            retriever = get_retriever()
            if not retriever:
                raise HTTPException(
                    status_code=503,
                    detail="Semantic search not available - embeddings not initialized"
                )
            
            # Verify file belongs to user if file_id is provided
            if file_id:
                from services.file_service import get_file_metadata
                file_info = await get_file_metadata(file_id, current_user)
                if not file_info:
                    raise HTTPException(status_code=404, detail="File not found")
            
            # Retrieve context (filtered by user_id) - async for MongoDB
            context = await retriever.retrieve_context(
                query=query,
                n_columns=n_results,
                n_relationships=min(5, n_results // 2),
                file_filter=file_id,
                user_id=current_user.id
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
    async def get_vector_store_stats(current_user: UserInDB = Depends(get_current_user)):
        """Get statistics about the vector store (requires authentication)."""
        try:
            vector_store = get_vector_store()
            if not vector_store:
                return {
                    "available": False,
                    "message": "Vector store not initialized"
                }
            
            stats = await vector_store.get_collection_stats(user_id=current_user.id)
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
    async def remove_file_from_index(
        file_id: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Remove a file from the semantic index (requires authentication)."""
        try:
            # Verify file belongs to user
            from services.file_service import get_file_metadata
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            vector_store = get_vector_store()
            if not vector_store:
                raise HTTPException(
                    status_code=503,
                    detail="Vector store not available"
                )
            
            success = await vector_store.delete_file(file_id, user_id=current_user.id)
            
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

def get_agent_tools(user_id: Optional[str] = None):
    """
    Get common tools for all agents with MongoDB support.
    
    Args:
        user_id: User ID for multi-tenant filtering (required for MongoDB mode)
    """
    if not user_id:
        raise ValueError("user_id is required for MongoDB-based agent tools")
    
    # Use MongoDBExcelRetriever (has synchronous wrapper methods)
    try:
        from tools.mongodb_excel_retriever import MongoDBExcelRetriever
        
        excel_retriever = MongoDBExcelRetriever(user_id=user_id)
        logger.info(f"✓ Using MongoDBExcelRetriever for user_id: {user_id}")
    except ImportError as e:
        logger.error(f"Failed to import BackendExcelRetriever: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise ValueError("BackendExcelRetriever not available - MongoDB tools require MongoDB support")
    except Exception as e:
        logger.error(f"Failed to initialize BackendExcelRetriever: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise ValueError(f"Failed to initialize MongoDB retriever: {e}")
    
    data_calculator = DataCalculator()
    trend_analyzer = TrendAnalyzer()
    comparative_analyzer = ComparativeAnalyzer()
    kpi_calculator = KPICalculator()
    graph_generator = GraphGenerator()
    
    # Get semantic retriever (already supports user_id)
    semantic_retriever = get_retriever()
    if not semantic_retriever:
        logger.warning("Semantic retriever not available - agent will have limited capabilities")
    
    # Create LangChain tools
    tools = []
    
    if semantic_retriever:
        # Pass user_id to semantic retriever for filtering
        tools.append(create_excel_retriever_tool(excel_retriever, semantic_retriever, user_id=user_id))
    tools.append(create_data_calculator_tool(data_calculator))
    tools.append(create_trend_analyzer_tool(trend_analyzer, excel_retriever, semantic_retriever, user_id=user_id))
    tools.append(create_comparative_analyzer_tool(comparative_analyzer, excel_retriever, semantic_retriever, user_id=user_id))
    tools.append(create_kpi_calculator_tool(kpi_calculator, excel_retriever, semantic_retriever, user_id=user_id))
    tools.append(create_graph_generator_tool(graph_generator, excel_retriever, semantic_retriever, user_id=user_id))
    
    return tools

def get_agent_instance(provider: str = "groq", user_id: Optional[str] = None):
    """
    Get or create agent instance for specified provider.
    
    Args:
        provider: Provider name ("groq" or "gemini")
        user_id: User ID for multi-tenant filtering (creates user-specific agent instance)
    """
    global _agent_instances
    
    if not AGENT_AVAILABLE:
        return None
    
    provider = provider.lower()
    
    # Create cache key with user_id for multi-tenant support
    cache_key = f"{provider}_{user_id}" if user_id else provider
    
    # Return cached instance if available
    if cache_key in _agent_instances and _agent_instances[cache_key] is not None:
        return _agent_instances[cache_key]
    
    try:
        # Get tools with user_id for multi-tenant filtering
        logger.info(f"Initializing {provider} agent for user_id: {user_id}")
        tools = get_agent_tools(user_id=user_id)
        logger.info(f"✓ Got {len(tools)} tools for agent")
        
        # Create agent based on provider
        if provider == "gemini":
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.error("GEMINI_API_KEY not found in environment variables")
                raise ValueError("GEMINI_API_KEY is required for Gemini agent")
            
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
            logger.info(f"Creating Gemini agent with model: {model_name}")
            
            _agent_instances[cache_key] = ExcelAgent(
                tools=tools,
                provider="gemini",
                model_name=model_name,
                gemini_api_key=gemini_api_key
            )
            logger.info(f"✓ Gemini agent initialized successfully with model: {model_name} (user_id: {user_id})")
            
        elif provider == "groq":
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("GROQ_API_KEY not found in environment variables")
                raise ValueError("GROQ_API_KEY is required for Groq agent")
            
            model_name = os.getenv("AGENT_MODEL_NAME", "meta-llama/llama-4-maverick-17b-128e-instruct")
            
            _agent_instances[cache_key] = ExcelAgent(
                tools=tools,
                provider="groq",
                model_name=model_name,
                groq_api_key=groq_api_key
            )
            logger.info(f"✓ Groq agent initialized successfully with model: {model_name} (user_id: {user_id})")
        else:
            raise ValueError(f"Unknown provider: {provider}. Must be 'groq' or 'gemini'")
        
    except Exception as e:
        logger.error(f"Failed to initialize {provider} agent: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        _agent_instances[cache_key] = None
        return None
    
    return _agent_instances[cache_key]


class AgentQueryRequest(BaseModel):
    """Request model for agent query."""
    question: str
    provider: Optional[str] = "gemini"  # "groq" or "gemini"
    file_id: Optional[str] = None
    conversation_id: Optional[str] = None
    date_range: Optional[Dict[str, Optional[str]]] = None


if MONGODB_AVAILABLE:
    # Try to import MongoDB-based agent system
    try:
        from agent.mongodb_agent import execute_agent_query
        from agent.agent_schemas import AgentQueryRequest as NewAgentQueryRequest
        MONGODB_AGENT_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"MongoDB agent system not available: {str(e)}")
        MONGODB_AGENT_AVAILABLE = False
    
    @app.post("/api/agent/query")
    async def agent_query(
        request: AgentQueryRequest,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Process a natural language query using the MongoDB-based agent (requires authentication)."""
        try:
            # Use MongoDB-based agent if available
            if MONGODB_AGENT_AVAILABLE:
                provider = request.provider.lower() if request.provider else "gemini"
                if provider not in ["groq", "gemini"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid provider: {provider}. Must be 'groq' or 'gemini'"
                    )
                
                # Execute query using MongoDB agent
                result = await execute_agent_query(
                    question=request.question,
                    user_id=str(current_user.id),
                    file_id=request.file_id,
                    provider=provider,
                    conversation_id=request.conversation_id,
                    date_range=request.date_range
                )
                
                return result
            else:
                # Fallback to old agent system
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
                
                # Get user-specific agent instance
                user_id = str(current_user.id)
                agent = get_agent_instance(provider=provider, user_id=user_id)
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
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))
else:
    @app.post("/api/agent/query")
    async def agent_query(request: AgentQueryRequest):
        """Process a natural language query using the agent (MongoDB not available)."""
        raise HTTPException(
            status_code=503,
            detail="MongoDB not available - agent chat requires MongoDB for multi-tenant support"
        )


if MONGODB_AVAILABLE:
    @app.get("/api/agent/status")
    async def get_agent_status(current_user: UserInDB = Depends(get_current_user)):
        """Get agent system status for all providers (requires authentication)."""
        try:
            prompt_eng_available = PROMPT_ENGINEERING_AVAILABLE if 'PROMPT_ENGINEERING_AVAILABLE' in globals() else False
            
            # Check MongoDB agent availability
            groq_available = False
            groq_model = None
            groq_error = None
            gemini_available = False
            gemini_model = None
            gemini_error = None
            mongodb_agent_available = False
            
            # Try to use MongoDB agent system first
            try:
                from agent.mongodb_agent import get_llm_instance
                mongodb_agent_available = True
                
                # Test Groq LLM instance
                try:
                    groq_llm = get_llm_instance(provider="groq", temperature=0.0)
                    groq_available = groq_llm is not None
                    groq_model = os.getenv("AGENT_MODEL_NAME", "meta-llama/llama-4-maverick-17b-128e-instruct")
                    logger.info(f"✓ Groq LLM available: {groq_model}")
                except Exception as e:
                    groq_error = str(e)
                    logger.error(f"Groq LLM test failed: {e}")
                
                # Test Gemini LLM instance
                try:
                    gemini_llm = get_llm_instance(provider="gemini", temperature=0.0)
                    gemini_available = gemini_llm is not None
                    gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
                    logger.info(f"✓ Gemini LLM available: {gemini_model}")
                except Exception as e:
                    gemini_error = str(e)
                    logger.error(f"Gemini LLM test failed: {e}")
            except ImportError:
                # Fallback to old agent system check
                mongodb_agent_available = False
                user_id = str(current_user.id)
                try:
                    groq_agent = get_agent_instance(provider="groq", user_id=user_id)
                    groq_available = groq_agent is not None
                    if groq_agent:
                        groq_model = groq_agent.model_name
                except Exception as e:
                    groq_error = str(e)
                
                try:
                    gemini_agent = get_agent_instance(provider="gemini", user_id=user_id)
                    gemini_available = gemini_agent is not None
                    if gemini_agent:
                        gemini_model = gemini_agent.model_name
                except Exception as e:
                    gemini_error = str(e)
            
            return {
                "available": mongodb_agent_available and (groq_available or gemini_available),
                "embeddings_available": EMBEDDINGS_AVAILABLE,
                "prompt_engineering": prompt_eng_available,
                "providers": {
                    "groq": {
                        "available": groq_available,
                        "initialized": groq_available,
                        "model_name": groq_model or os.getenv("AGENT_MODEL_NAME", "meta-llama/llama-4-maverick-17b-128e-instruct"),
                        "api_key_set": bool(os.getenv("GROQ_API_KEY")),
                        "error": groq_error if not groq_available else None
                    },
                    "gemini": {
                        "available": gemini_available,
                        "initialized": gemini_available,
                        "model_name": gemini_model or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"),
                        "api_key_set": bool(os.getenv("GEMINI_API_KEY")),
                        "error": gemini_error if not gemini_available else None
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting agent status: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "available": False,
                "error": str(e),
                "providers": {
                    "groq": {"available": False},
                    "gemini": {"available": False}
                }
            }

    @app.get("/api/agent/suggestions")
    async def get_agent_suggestions(
        regenerate: bool = Query(False, description="Force regeneration of suggestions using Gemini API"),
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get dynamic question suggestions from verified QA bank and fallback to generated suggestions (requires authentication).
        
        Args:
            regenerate: If True, skip QA bank and force regeneration using Gemini API
        """
        try:
            from services.file_service import get_user_files
            from services.question_generator_service import MongoDBQuestionGenerator
            from database import get_database
            
            db = get_database()
            text_queries = []
            graph_queries = []
            
            logger.info(f"Getting agent suggestions - regenerate={regenerate}, user_id={current_user.id}")
            
            # First, try to get verified questions from QA bank (unless regenerate is True)
            if not regenerate:
                try:
                    qa_bank_collection = db["qa_bank"]
                    
                    # Get verified questions for this user - get more to have better variety
                    # Use random sampling to get different questions each time
                    all_verified = await qa_bank_collection.find({
                        "user_id": current_user.id,
                        "verified": True
                    }).to_list(length=None)  # Get all verified questions
                    
                    if all_verified and len(all_verified) > 0:
                        # Randomly sample up to 100 questions for variety
                        verified_questions = random.sample(all_verified, min(100, len(all_verified)))
                        
                        # Categorize verified questions more intelligently
                        for q in verified_questions:
                            question_text = q.get("question_text", q.get("question", ""))
                            question_type = q.get("question_type", q.get("type", "")).lower()
                            expects_chart = q.get("expects_chart", False)
                            
                            if not question_text:
                                continue
                            
                            question_lower = question_text.lower()
                            
                            # Check if question mentions chart/graph/visualization
                            chart_keywords = ["chart", "graph", "plot", "visualize", "show", "display", "trend", "comparison", "bar chart", "line chart", "pie chart", "scatter", "visualization"]
                            has_chart_keyword = any(keyword in question_lower for keyword in chart_keywords)
                            
                            # Questions that typically need charts
                            chart_indicators = [
                                "which", "who", "compare", "comparison", "distribution", 
                                "over time", "by", "across", "between", "top", "bottom",
                                "highest", "lowest", "most", "least", "rank"
                            ]
                            has_chart_indicator = any(indicator in question_lower for indicator in chart_indicators)
                            
                            # Categorize based on type, keywords, and question structure
                            # More nuanced categorization
                            is_graph_query = (
                                expects_chart or 
                                has_chart_keyword or 
                                question_type in ["trend", "comparative", "distribution"] or
                                (has_chart_indicator and question_type in ["comparative"]) or
                                (question_type == "aggregation" and has_chart_indicator and ("which" in question_lower or "who" in question_lower))
                            )
                            
                            # Simple aggregation questions (what is the total/average) are text queries
                            is_simple_aggregation = (
                                question_type == "aggregation" and 
                                not has_chart_keyword and
                                not has_chart_indicator and
                                ("what is" in question_lower or "what are" in question_lower or "how many" in question_lower)
                            )
                            
                            if is_graph_query and not is_simple_aggregation:
                                if question_text not in graph_queries:
                                    graph_queries.append(question_text)
                            else:
                                if question_text not in text_queries:
                                    text_queries.append(question_text)
                        
                        # Shuffle to get variety, then limit - use random sample for more variety
                        random.shuffle(text_queries)
                        random.shuffle(graph_queries)
                        
                        # Randomly sample from available questions to get different sets each time
                        # Take a random subset to ensure variety
                        if len(text_queries) > 12:
                            # Randomly select 12 from available text queries
                            text_queries = random.sample(text_queries, min(12, len(text_queries)))
                        else:
                            text_queries = text_queries[:12]
                        
                        if len(graph_queries) > 12:
                            # Randomly select 12 from available graph queries
                            graph_queries = random.sample(graph_queries, min(12, len(graph_queries)))
                        else:
                            graph_queries = graph_queries[:12]
                        
                        # Return verified questions with randomization
                        return {
                            "success": True,
                            "text_queries": text_queries,
                            "graph_queries": graph_queries,
                            "source": "qa_bank",
                            "total_verified": len(verified_questions),
                            "text_count": len(text_queries),
                            "graph_count": len(graph_queries)
                        }
                except Exception as e:
                    logger.warning(f"Could not fetch from QA bank, falling back to generated suggestions: {str(e)}")
            else:
                logger.info("Regenerate flag is True, skipping QA bank and generating new suggestions with Gemini")
            
            # Fallback: Generate suggestions using Gemini API based on actual data
            files = await get_user_files(current_user, deduplicate=True)
            
            if not files:
                return {
                    "success": True,
                    "text_queries": text_queries[:12] if text_queries else [],
                    "graph_queries": graph_queries[:12] if graph_queries else [],
                    "message": "No files uploaded yet. Upload files to get suggestions.",
                    "source": "generated"
                }
            
            # Collect detailed schema information from all files
            all_files_info = []
            tables_collection = db["tables"]
            
            for file_info in files:
                file_id = file_info.get("file_id")
                filename = file_info.get("filename", "Unknown")
                
                # Get actual data schema from MongoDB
                try:
                    # Get sample rows and column info from actual data
                    sample_query = {
                        "user_id": current_user.id,
                        "file_id": file_id,
                        "table_name": "Sheet1"
                    }
                    
                    sample_rows = await tables_collection.find(sample_query).limit(5).to_list(length=5)
                    
                    if sample_rows:
                        # Extract columns from actual data
                        first_row = sample_rows[0].get("row", {})
                        columns_info = {}
                        numeric_cols = []
                        date_cols = []
                        text_cols = []
                        
                        for col_name, col_value in first_row.items():
                            if col_value is None:
                                continue
                            
                            col_type = type(col_value).__name__
                            columns_info[col_name] = {
                                "type": col_type,
                                "sample_value": str(col_value)[:50] if col_value else None
                            }
                            
                            # Categorize columns
                            if col_type in ["int", "float", "Decimal"] or isinstance(col_value, (int, float)):
                                numeric_cols.append(col_name)
                            elif col_type in ["datetime", "date"] or "date" in col_name.lower() or "time" in col_name.lower():
                                date_cols.append(col_name)
                            else:
                                text_cols.append(col_name)
                        
                        # Get row count
                        row_count = await tables_collection.count_documents(sample_query)
                        
                        all_files_info.append({
                            "filename": filename,
                            "file_id": file_id,
                            "table_name": "Sheet1",
                            "columns": columns_info,
                            "numeric_columns": numeric_cols,
                            "date_columns": date_cols,
                            "text_columns": text_cols,
                            "row_count": row_count,
                            "sample_rows": [r.get("row", {}) for r in sample_rows[:3]]
                        })
                except Exception as e:
                    logger.warning(f"Error getting schema for file {file_id}: {str(e)}")
                    continue
            
            # Use Gemini API to generate questions based on actual data
            try:
                from agent.mongodb_agent import get_llm_instance
                gemini_llm = get_llm_instance(provider="gemini", temperature=0.7)
                
                # Build context for Gemini
                schema_context = "Available data files and their schemas:\n\n"
                for file_info in all_files_info:
                    schema_context += f"File: {file_info['filename']} (file_id: {file_info['file_id']}, {file_info['row_count']} rows)\n"
                    schema_context += f"Table: {file_info['table_name']}\n"
                    schema_context += f"Columns:\n"
                    for col_name, col_info in file_info['columns'].items():
                        schema_context += f"  - {col_name} ({col_info['type']}): sample = {col_info.get('sample_value', 'N/A')}\n"
                    schema_context += f"\nNumeric columns: {', '.join(file_info['numeric_columns'])}\n"
                    schema_context += f"Date columns: {', '.join(file_info['date_columns'])}\n"
                    schema_context += f"Text columns: {', '.join(file_info['text_columns'])}\n\n"
                
                # Generate text queries (aggregation questions)
                # Add variety by asking for different question types
                text_prompt = f"""Based on the following database schema, generate 20 diverse natural language questions that users might ask to get text-based answers.

{schema_context}

Generate a VARIETY of questions including:
1. Aggregations: total, average, mean, sum, count, min, max, median
2. Comparisons: compare values between different entities
3. Calculations: percentages, ratios, differences
4. Specific lookups: find specific values or records
5. Statistical questions: variance, standard deviation, ranges

IMPORTANT:
- Use ACTUAL column names from the schema above
- Make each question UNIQUE and different from others
- Vary the question phrasing (don't repeat the same pattern)
- Don't ask for charts/visualizations (those will be separate)
- Be creative and think of different ways to ask about the data

Return ONLY a JSON array of question strings, no explanations. Example format:
["What is the total opening stock in Kg?", "What is the average downtime in hours?", "How many maintenance records are there?", ...]

Generate 20 diverse questions:"""
                
                logger.info("Calling Gemini API to generate text queries...")
                text_response = gemini_llm.invoke(text_prompt)
                text_response_text = text_response.content if hasattr(text_response, 'content') else str(text_response)
                logger.debug(f"Gemini text response: {text_response_text[:500]}")
                
                # Parse JSON array from response
                try:
                    # Extract JSON array from response
                    json_match = re.search(r'\[.*?\]', text_response_text, re.DOTALL)
                    if json_match:
                        text_queries_generated = json.loads(json_match.group())
                        if isinstance(text_queries_generated, list):
                            text_queries.extend(text_queries_generated)
                            logger.info(f"Successfully parsed {len(text_queries_generated)} text queries from Gemini")
                        else:
                            logger.warning(f"Gemini returned non-list for text queries: {type(text_queries_generated)}")
                    else:
                        # Fallback: split by lines and clean
                        lines = [l.strip().strip('"').strip("'") for l in text_response_text.split('\n') if l.strip() and not l.strip().startswith('#')]
                        text_queries.extend([l for l in lines if l and len(l) > 10][:20])
                        logger.info(f"Used fallback parsing, extracted {len([l for l in lines if l and len(l) > 10][:20])} text queries")
                except Exception as e:
                    logger.warning(f"Error parsing text queries from Gemini: {str(e)}")
                    logger.debug(f"Full response was: {text_response_text}")
                
                # Generate graph queries (visualization questions)
                graph_prompt = f"""Based on the following database schema, generate 20 diverse natural language questions that users might ask to visualize data (charts, graphs, trends).

{schema_context}

Generate a VARIETY of visualization questions including:
1. Bar charts: comparisons, rankings, distributions
2. Line charts: trends over time, time series
3. Pie charts: proportions, percentages, distributions
4. Scatter plots: correlations, relationships
5. Ranking questions: "which", "who", "top N", "bottom N"
6. Comparison questions: compare entities side-by-side
7. Trend questions: changes over time, patterns

IMPORTANT:
- Use ACTUAL column names from the schema above
- Make each question UNIQUE and different from others
- Vary the question phrasing and chart types
- Explicitly mention chart types when appropriate
- Be creative with different visualization scenarios

Return ONLY a JSON array of question strings, no explanations. Example format:
["Show opening stock by supplier as a bar chart", "Which operator has the highest number of entries?", "Display the trend of downtime over time as a line chart", ...]

Generate 20 diverse visualization questions:"""
                
                logger.info("Calling Gemini API to generate graph queries...")
                graph_response = gemini_llm.invoke(graph_prompt)
                graph_response_text = graph_response.content if hasattr(graph_response, 'content') else str(graph_response)
                logger.debug(f"Gemini graph response: {graph_response_text[:500]}")
                
                # Parse JSON array from response
                try:
                    # Extract JSON array from response
                    json_match = re.search(r'\[.*?\]', graph_response_text, re.DOTALL)
                    if json_match:
                        graph_queries_generated = json.loads(json_match.group())
                        if isinstance(graph_queries_generated, list):
                            graph_queries.extend(graph_queries_generated)
                            logger.info(f"Successfully parsed {len(graph_queries_generated)} graph queries from Gemini")
                        else:
                            logger.warning(f"Gemini returned non-list for graph queries: {type(graph_queries_generated)}")
                    else:
                        # Fallback: split by lines and clean
                        lines = [l.strip().strip('"').strip("'") for l in graph_response_text.split('\n') if l.strip() and not l.strip().startswith('#')]
                        graph_queries.extend([l for l in lines if l and len(l) > 10][:20])
                        logger.info(f"Used fallback parsing, extracted {len([l for l in lines if l and len(l) > 10][:20])} graph queries")
                except Exception as e:
                    logger.warning(f"Error parsing graph queries from Gemini: {str(e)}")
                    logger.debug(f"Full response was: {graph_response_text}")
                
            except Exception as e:
                logger.error(f"Error generating suggestions with Gemini: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback to simple template-based generation
                all_numeric_cols = []
                all_date_cols = []
                all_text_cols = []
                
                for file_info in all_files_info:
                    all_numeric_cols.extend(file_info.get("numeric_columns", []))
                    all_date_cols.extend(file_info.get("date_columns", []))
                    all_text_cols.extend(file_info.get("text_columns", []))
                
                # Simple fallback queries
                if all_numeric_cols:
                    for col in list(set(all_numeric_cols))[:5]:
                        text_queries.append(f"What is the total {col.lower()}?")
                        text_queries.append(f"What is the average {col.lower()}?")
                
                if all_numeric_cols and all_text_cols:
                    metric_col = list(set(all_numeric_cols))[0] if all_numeric_cols else None
                    entity_col = list(set(all_text_cols))[0] if all_text_cols else None
                    if metric_col and entity_col:
                        graph_queries.append(f"Show {metric_col.lower()} by {entity_col.lower()} as a bar chart")
                        graph_queries.append(f"Which {entity_col.lower()} has the highest {metric_col.lower()}?")
            
            # Remove duplicates and limit
            text_queries = list(dict.fromkeys(text_queries))[:20]  # Max 20 text queries
            graph_queries = list(dict.fromkeys(graph_queries))[:20]  # Max 20 graph queries
            
            logger.info(f"Generated {len(text_queries)} text queries and {len(graph_queries)} graph queries using Gemini")
            
            # Collect column counts
            total_numeric = sum(len(f.get("numeric_columns", [])) for f in all_files_info)
            total_date = sum(len(f.get("date_columns", [])) for f in all_files_info)
            total_text = sum(len(f.get("text_columns", [])) for f in all_files_info)
            
            return {
                "success": True,
                "text_queries": text_queries,
                "graph_queries": graph_queries,
                "total_files": len(files),
                "source": "gemini" if regenerate else "generated",
                "total_columns": {
                    "numeric": total_numeric,
                    "date": total_date,
                    "text": total_text
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "text_queries": [],
                "graph_queries": [],
                "error": str(e)
            }

    @app.post("/api/agent/suggestions/regenerate")
    async def regenerate_agent_suggestions(current_user: UserInDB = Depends(get_current_user)):
        """Regenerate question suggestions using Gemini API based on actual database data (requires authentication)."""
        # Use the same endpoint logic with regenerate=True
        try:
            from services.file_service import get_user_files
            from database import get_database
            
            db = get_database()
            text_queries = []
            graph_queries = []
            
            # Skip QA bank and go straight to Gemini generation
            logger.info("Regenerating suggestions using Gemini API")
            
            # Get files and generate with Gemini
            files = await get_user_files(current_user, deduplicate=True)
            
            if not files:
                return {
                    "success": True,
                    "text_queries": [],
                    "graph_queries": [],
                    "message": "No files uploaded yet. Upload files to get suggestions.",
                    "source": "generated"
                }
            
            # Collect detailed schema information from all files
            all_files_info = []
            tables_collection = db["tables"]
            
            for file_info in files:
                file_id = file_info.get("file_id")
                filename = file_info.get("filename", "Unknown")
                
                # Get actual data schema from MongoDB
                try:
                    sample_query = {
                        "user_id": current_user.id,
                        "file_id": file_id,
                        "table_name": "Sheet1"
                    }
                    
                    sample_rows = await tables_collection.find(sample_query).limit(5).to_list(length=5)
                    
                    if sample_rows:
                        first_row = sample_rows[0].get("row", {})
                        columns_info = {}
                        numeric_cols = []
                        date_cols = []
                        text_cols = []
                        
                        for col_name, col_value in first_row.items():
                            if col_value is None:
                                continue
                            
                            col_type = type(col_value).__name__
                            columns_info[col_name] = {
                                "type": col_type,
                                "sample_value": str(col_value)[:50] if col_value else None
                            }
                            
                            if col_type in ["int", "float", "Decimal"] or isinstance(col_value, (int, float)):
                                numeric_cols.append(col_name)
                            elif col_type in ["datetime", "date"] or "date" in col_name.lower() or "time" in col_name.lower():
                                date_cols.append(col_name)
                            else:
                                text_cols.append(col_name)
                        
                        row_count = await tables_collection.count_documents(sample_query)
                        
                        all_files_info.append({
                            "filename": filename,
                            "file_id": file_id,
                            "table_name": "Sheet1",
                            "columns": columns_info,
                            "numeric_columns": numeric_cols,
                            "date_columns": date_cols,
                            "text_columns": text_cols,
                            "row_count": row_count,
                            "sample_rows": [r.get("row", {}) for r in sample_rows[:3]]
                        })
                except Exception as e:
                    logger.warning(f"Error getting schema for file {file_id}: {str(e)}")
                    continue
            
            # Use Gemini API to generate questions
            from agent.mongodb_agent import get_llm_instance
            gemini_llm = get_llm_instance(provider="gemini", temperature=0.7)
            
            # Build context for Gemini
            schema_context = "Available data files and their schemas:\n\n"
            for file_info in all_files_info:
                schema_context += f"File: {file_info['filename']} (file_id: {file_info['file_id']}, {file_info['row_count']} rows)\n"
                schema_context += f"Table: {file_info['table_name']}\n"
                schema_context += f"Columns:\n"
                for col_name, col_info in file_info['columns'].items():
                    schema_context += f"  - {col_name} ({col_info['type']}): sample = {col_info.get('sample_value', 'N/A')}\n"
                schema_context += f"\nNumeric columns: {', '.join(file_info['numeric_columns'])}\n"
                schema_context += f"Date columns: {', '.join(file_info['date_columns'])}\n"
                schema_context += f"Text columns: {', '.join(file_info['text_columns'])}\n\n"
            
            # Generate text queries
            text_prompt = f"""Based on the following database schema, generate 15 natural language questions that users might ask to get text-based answers (aggregations, calculations, comparisons).

{schema_context}

Generate questions that:
1. Ask for aggregations (total, average, mean, sum, count, min, max)
2. Ask for comparisons between entities
3. Ask for specific values or calculations
4. Use actual column names from the schema
5. Are natural and conversational
6. Don't ask for charts/visualizations (those will be separate)

Return ONLY a JSON array of question strings, no explanations. Example format:
["What is the total opening stock in Kg?", "What is the average downtime in hours?", ...]

Generate 15 questions:"""
            
            text_response = gemini_llm.invoke(text_prompt)
            text_response_text = text_response.content if hasattr(text_response, 'content') else str(text_response)
            
            try:
                json_match = re.search(r'\[.*?\]', text_response_text, re.DOTALL)
                if json_match:
                    text_queries_generated = json.loads(json_match.group())
                    text_queries.extend(text_queries_generated)
                else:
                    lines = [l.strip().strip('"').strip("'") for l in text_response_text.split('\n') if l.strip() and not l.strip().startswith('#')]
                    text_queries.extend([l for l in lines if l and len(l) > 10][:15])
            except Exception as e:
                logger.warning(f"Error parsing text queries from Gemini: {str(e)}")
            
            # Generate graph queries
            graph_prompt = f"""Based on the following database schema, generate 15 natural language questions that users might ask to visualize data (charts, graphs, trends).

{schema_context}

Generate questions that:
1. Ask for charts/graphs/visualizations (bar chart, line chart, pie chart, etc.)
2. Ask for trends over time
3. Ask for comparisons that need visual representation
4. Ask "which", "who", "top N", "bottom N" questions
5. Use actual column names from the schema
6. Are natural and conversational
7. Explicitly mention chart types when appropriate

Return ONLY a JSON array of question strings, no explanations. Example format:
["Show opening stock by supplier as a bar chart", "Which operator has the highest number of entries?", ...]

Generate 15 questions:"""
            
            graph_response = gemini_llm.invoke(graph_prompt)
            graph_response_text = graph_response.content if hasattr(graph_response, 'content') else str(graph_response)
            
            try:
                json_match = re.search(r'\[.*?\]', graph_response_text, re.DOTALL)
                if json_match:
                    graph_queries_generated = json.loads(json_match.group())
                    graph_queries.extend(graph_queries_generated)
                else:
                    lines = [l.strip().strip('"').strip("'") for l in graph_response_text.split('\n') if l.strip() and not l.strip().startswith('#')]
                    graph_queries.extend([l for l in lines if l and len(l) > 10][:15])
            except Exception as e:
                logger.warning(f"Error parsing graph queries from Gemini: {str(e)}")
            
            # Remove duplicates and limit
            text_queries = list(dict.fromkeys(text_queries))[:20]
            graph_queries = list(dict.fromkeys(graph_queries))[:20]
            
            return {
                "success": True,
                "text_queries": text_queries,
                "graph_queries": graph_queries,
                "total_files": len(files),
                "source": "gemini_regenerated"
            }
            
        except Exception as e:
            logger.error(f"Error regenerating suggestions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "text_queries": [],
                "graph_queries": [],
                "error": str(e)
            }
else:
    @app.get("/api/agent/status")
    async def get_agent_status():
        """Get agent system status for all providers (MongoDB not available)."""
        return {
            "available": False,
            "error": "MongoDB not available - agent chat requires MongoDB for multi-tenant support",
            "providers": {
                "groq": {"available": False},
                "gemini": {"available": False}
            }
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

if MONGODB_AVAILABLE:
    @app.get("/api/visualizations/data/all")
    async def get_all_visualization_data(current_user: UserInDB = Depends(get_current_user)):
        """Get all visualization data for user's files - DYNAMIC VERSION (requires authentication)"""
        try:
            from services.file_service import get_user_files, get_file_from_gridfs
            
            # Get all user's files
            files = await get_user_files(current_user)
            
            all_visualizations = {}
            
            for file_info in files:
                file_id = file_info.get("file_id")
                if not file_id:
                    continue
                
                try:
                    # Get file content from GridFS
                    file_content = await get_file_from_gridfs(file_id, current_user)
                    
                    # Generate visualizations dynamically
                    viz_data = await dynamic_visualizer.generate_visualizations_for_file(
                        file_id, file_info, file_content
                    )
                    
                    if viz_data:
                        all_visualizations[file_id] = viz_data
                        
                except Exception as e:
                    logger.warning(f"Error generating visualizations for file {file_id}: {e}")
                    continue
            
            return {
                "success": True,
                "visualizations": all_visualizations,
                "file_count": len(all_visualizations)
            }
        except Exception as e:
            logger.error(f"Error generating visualization data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/visualizations/file/{file_id}")
    async def get_file_visualizations(
        file_id: str,
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get visualizations for a specific file (requires authentication)"""
        try:
            from services.file_service import get_file_metadata, get_file_from_gridfs
            
            # Get file metadata
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get file content from GridFS
            file_content = await get_file_from_gridfs(file_id, current_user)
            
            # Generate visualizations dynamically
            viz_data = await dynamic_visualizer.generate_visualizations_for_file(
                file_id, file_info, file_content
            )
            
            if not viz_data:
                raise HTTPException(status_code=500, detail="Failed to generate visualizations")
            
            return {
                "success": True,
                "visualization": viz_data
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating visualizations for file {file_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/visualizations/file/{file_id}/data")
    async def get_file_data(
        file_id: str,
        sheet_name: Optional[str] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(100, ge=1, le=1000),
        filters: Optional[str] = Query(None, description="JSON string of filters"),
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get paginated and filtered data from a file (requires authentication)"""
        try:
            import json
            import pandas as pd
            import numpy as np
            import io
            
            from services.file_service import get_file_metadata, get_file_from_gridfs
            
            # Get file metadata
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get file content from GridFS
            file_content = await get_file_from_gridfs(file_id, current_user)
            
            file_type = file_info.get("file_type", "csv")
            
            # Load DataFrame
            if file_type.lower() in ['xlsx', 'xls']:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                if sheet_name:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                else:
                    # Use first sheet if no sheet specified
                    df = pd.read_excel(excel_file, sheet_name=excel_file.sheet_names[0])
                excel_file.close()
            else:
                # Handle CSV files - try different encodings
                try:
                    df = pd.read_csv(io.BytesIO(file_content))
                except UnicodeDecodeError:
                    # Try with different encoding
                    df = pd.read_csv(io.BytesIO(file_content), encoding='latin-1')
            
            if df.empty:
                return {
                    "success": True,
                    "data": [],
                    "columns": [],
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_rows": 0,
                        "total_pages": 0
                    }
                }
            
            # Apply filters if provided
            if filters:
                try:
                    filter_dict = json.loads(filters)
                    for col, value in filter_dict.items():
                        if col in df.columns:
                            if isinstance(value, list):
                                df = df[df[col].isin(value)]
                            else:
                                df = df[df[col] == value]
                except Exception as e:
                    logger.warning(f"Error applying filters: {e}")
            
            # Pagination
            total_rows = len(df)
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)  # Ensure we don't go beyond dataframe
            paginated_df = df.iloc[start_idx:end_idx] if total_rows > 0 else df.iloc[0:0]
            
            # Convert to records
            records = paginated_df.to_dict('records')
            
            # Convert numpy types to Python types
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif isinstance(value, (np.integer, np.int64)):
                        record[key] = int(value)
                    elif isinstance(value, (np.floating, np.float64)):
                        record[key] = float(value)
                    elif isinstance(value, pd.Timestamp):
                        record[key] = value.isoformat()
                    else:
                        record[key] = str(value) if value is not None else None
            
            return {
                "success": True,
                "data": records,
                "columns": list(df.columns),
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_rows": total_rows,
                    "total_pages": (total_rows + page_size - 1) // page_size if total_rows > 0 else 0
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/visualizations/file/{file_id}/filter-options")
    async def get_file_filter_options(
        file_id: str,
        sheet_name: Optional[str] = Query(None),
        column: Optional[str] = Query(None),
        current_user: UserInDB = Depends(get_current_user)
    ):
        """Get unique filter options for a column (requires authentication)"""
        try:
            import pandas as pd
            import io
            
            from services.file_service import get_file_metadata, get_file_from_gridfs
            
            # Get file metadata
            file_info = await get_file_metadata(file_id, current_user)
            if not file_info:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Get file content from GridFS
            file_content = await get_file_from_gridfs(file_id, current_user)
            
            file_type = file_info.get("file_type", "csv")
            
            # Load DataFrame
            if file_type.lower() in ['xlsx', 'xls']:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                if sheet_name:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(excel_file, sheet_name=excel_file.sheet_names[0])
                excel_file.close()
            else:
                df = pd.read_csv(io.BytesIO(file_content))
            
            # If column specified, return unique values for that column
            if column and column in df.columns:
                unique_values = df[column].dropna().unique().tolist()
                # Convert to strings and limit to 100 values
                unique_values = [str(v) for v in unique_values[:100]]
                return {
                    "success": True,
                    "column": column,
                    "options": unique_values
                }
            
            # Otherwise return all columns with their types
            column_info = {}
            for col in df.columns:
                if df[col].dtype == 'object':
                    unique_count = df[col].nunique()
                    if unique_count <= 50:
                        column_info[col] = {
                            "type": "categorical",
                            "unique_count": int(unique_count),
                            "options": [str(v) for v in df[col].dropna().unique().tolist()[:50]]
                        }
                    else:
                        column_info[col] = {
                            "type": "text",
                            "unique_count": int(unique_count)
                        }
                elif pd.api.types.is_numeric_dtype(df[col]):
                    column_info[col] = {
                        "type": "numeric",
                        "min": float(df[col].min()) if not df[col].isna().all() else None,
                        "max": float(df[col].max()) if not df[col].isna().all() else None
                    }
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    column_info[col] = {
                        "type": "date",
                        "min": df[col].min().isoformat() if not df[col].isna().all() else None,
                        "max": df[col].max().isoformat() if not df[col].isna().all() else None
                    }
                else:
                    column_info[col] = {
                        "type": "unknown"
                    }
            
            return {
                "success": True,
                "columns": column_info
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
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
