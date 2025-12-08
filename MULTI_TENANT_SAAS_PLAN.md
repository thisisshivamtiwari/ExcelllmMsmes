# 🏢 Multi-Tenant SaaS Architecture Plan

**Project**: ExcelLLM MSME → Universal Data Analytics Platform  
**Goal**: Transform into multi-tenant SaaS with user authentication, industry selection, and MongoDB storage  
**Date**: December 4, 2025

---

## 📋 Executive Summary

Transform the current single-tenant system into a **production-ready multi-tenant SaaS platform** where:
- ✅ Users sign up with email/password
- ✅ Users select their industry from dropdown
- ✅ Users upload data specific to their industry
- ✅ All data is isolated per user
- ✅ MongoDB stores all user data, files, and metadata
- ✅ Users can ask questions on their own data

---

## 🎯 Requirements Analysis

### **Current System:**
- ❌ No authentication (anyone can access)
- ❌ No user isolation (all files global)
- ❌ File system storage (`uploaded_files/` directory)
- ❌ No industry selection
- ❌ No user accounts

### **Target System:**
- ✅ JWT-based authentication
- ✅ User-specific data isolation
- ✅ MongoDB for all persistent data
- ✅ Industry selection dropdown
- ✅ User accounts with email/password
- ✅ Per-user file storage
- ✅ Per-user vector stores
- ✅ Per-user chat history

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + Vite + TailwindCSS                                  │
│  - Login/Signup Pages                                        │
│  - Industry Selection                                        │
│  - Protected Routes (Auth Required)                          │
│  - User Dashboard                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         │ JWT Tokens
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND API                             │
│  FastAPI + Python                                            │
│  - Authentication Endpoints                                  │
│  - User Management                                           │
│  - File Upload (with user context)                           │
│  - Agent Queries (with user context)                         │
│  - JWT Middleware                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ MongoDB Driver (Motor/PyMongo)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      MONGODB DATABASE                        │
│  Collections:                                                │
│  - users (email, password_hash, industry, created_at)       │
│  - files (user_id, file_id, metadata, industry)              │
│  - vector_stores (user_id, file_id, embeddings)             │
│  - chat_history (user_id, queries, responses)                │
│  - industries (name, description, schema_templates)          │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ File Storage
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FILE STORAGE (Optional)                    │
│  Option 1: MongoDB GridFS (recommended)                      │
│  Option 2: File System (user_id/industry/file_id)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Database Schema Design

### **1. Users Collection**
```javascript
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "password_hash": "$2b$12$...",  // bcrypt hashed
  "industry": "manufacturing",     // Selected from dropdown
  "created_at": ISODate("2025-12-04T..."),
  "updated_at": ISODate("2025-12-04T..."),
  "is_active": true,
  "last_login": ISODate("2025-12-04T..."),
  "profile": {
    "name": "John Doe",
    "company": "ABC Corp"
  }
}
```

### **2. Files Collection**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),      // Reference to users
  "file_id": "uuid-string",
  "original_filename": "production_data.csv",
  "industry": "manufacturing",
  "file_type": "csv",
  "file_size_bytes": 12345,
  "uploaded_at": ISODate("2025-12-04T..."),
  "metadata": {
    "columns": ["Date", "Product", "Quantity"],
    "row_count": 1000,
    "sheet_names": ["Sheet1"]
  },
  "storage": {
    "type": "gridfs",              // or "filesystem"
    "gridfs_id": ObjectId("..."),  // If using GridFS
    "file_path": "user_id/industry/file_id.csv"  // If filesystem
  },
  "is_indexed": false,
  "indexed_at": ISODate("...")
}
```

### **3. Vector Stores Collection**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "file_id": ObjectId("..."),       // Reference to files
  "vector_store_type": "chromadb",  // or "mongodb_atlas"
  "embeddings": [
    {
      "chunk_id": "chunk-1",
      "text": "Date: 2024-01-01, Product: Widget-A, Quantity: 100",
      "embedding": [0.1, 0.2, ...],  // Vector array
      "metadata": {
        "row_index": 0,
        "columns": ["Date", "Product", "Quantity"]
      }
    }
  ],
  "created_at": ISODate("2025-12-04T..."),
  "updated_at": ISODate("2025-12-04T...")
}
```

### **4. Chat History Collection**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "session_id": "session-uuid",
  "query": "What is the total production quantity?",
  "response": "The total production quantity is 237,525 units.",
  "provider": "gemini",
  "model_name": "gemini-2.5-flash",
  "reasoning_steps": [...],
  "intermediate_steps": [...],
  "files_used": [ObjectId("..."), ObjectId("...")],
  "created_at": ISODate("2025-12-04T...")
}
```

### **5. Industries Collection** (Pre-populated)
```javascript
{
  "_id": ObjectId("..."),
  "name": "manufacturing",
  "display_name": "Manufacturing",
  "description": "Production, quality control, maintenance data",
  "icon": "🏭",
  "schema_templates": [
    {
      "name": "Production Logs",
      "columns": ["Date", "Product", "Target_Qty", "Actual_Qty"],
      "description": "Daily production tracking"
    }
  ],
  "created_at": ISODate("2025-12-04T...")
}
```

---

## 🔐 Authentication Flow

### **1. Signup Flow**
```
User → Frontend Signup Form
  ↓
POST /api/auth/signup
  {
    "email": "user@example.com",
    "password": "secure123",
    "industry": "manufacturing",
    "name": "John Doe"
  }
  ↓
Backend:
  1. Validate email format
  2. Check if email exists
  3. Hash password (bcrypt)
  4. Create user in MongoDB
  5. Generate JWT token
  6. Return token + user info
  ↓
Frontend:
  - Store JWT in localStorage/cookies
  - Redirect to dashboard
```

### **2. Login Flow**
```
User → Frontend Login Form
  ↓
POST /api/auth/login
  {
    "email": "user@example.com",
    "password": "secure123"
  }
  ↓
Backend:
  1. Find user by email
  2. Verify password (bcrypt)
  3. Check if user is active
  4. Update last_login
  5. Generate JWT token
  6. Return token + user info
  ↓
Frontend:
  - Store JWT in localStorage/cookies
  - Redirect to dashboard
```

### **3. Protected Route Flow**
```
User → Frontend Protected Route
  ↓
Request includes: Authorization: Bearer <JWT>
  ↓
Backend Middleware:
  1. Extract JWT from header
  2. Verify JWT signature
  3. Check expiration
  4. Get user_id from JWT payload
  5. Fetch user from MongoDB
  6. Attach user to request context
  ↓
Route Handler:
  - Access request.user
  - Filter data by user_id
  - Return user-specific data
```

---

## 📁 File Storage Strategy

### **Option 1: MongoDB GridFS (Recommended)**
**Pros:**
- ✅ All data in one database
- ✅ Automatic replication
- ✅ Easy backup/restore
- ✅ No file system management

**Cons:**
- ⚠️ Slightly slower for very large files
- ⚠️ Requires MongoDB storage space

**Implementation:**
```python
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

# Store file
gridfs = AsyncIOMotorGridFSBucket(db)
file_id = await gridfs.upload_from_stream(
    filename=original_filename,
    source=file_content,
    metadata={"user_id": user_id, "industry": industry}
)

# Retrieve file
grid_out = await gridfs.open_download_stream(file_id)
file_content = await grid_out.read()
```

### **Option 2: File System with MongoDB Metadata**
**Pros:**
- ✅ Fast file access
- ✅ Can use CDN for large files
- ✅ Familiar file management

**Cons:**
- ⚠️ Requires file system management
- ⚠️ Backup complexity
- ⚠️ Scaling challenges

**Implementation:**
```python
# Store file
file_path = BASE_DIR / "user_data" / str(user_id) / industry / f"{file_id}.csv"
file_path.parent.mkdir(parents=True, exist_ok=True)
file_path.write_bytes(file_content)

# Store metadata in MongoDB
await files_collection.insert_one({
    "user_id": user_id,
    "file_id": file_id,
    "file_path": str(file_path),
    ...
})
```

**Recommendation**: Start with **GridFS** for simplicity, migrate to filesystem if needed.

---

## 🔧 Implementation Phases

### **Phase 1: MongoDB Setup & User Authentication** (Priority: HIGH)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Install MongoDB dependencies (`motor`, `pymongo`)
2. ✅ Create MongoDB connection module
3. ✅ Design database schema
4. ✅ Create user model and authentication service
5. ✅ Implement signup endpoint
6. ✅ Implement login endpoint
7. ✅ Implement JWT token generation/verification
8. ✅ Create authentication middleware
9. ✅ Create frontend login/signup pages
10. ✅ Add protected route wrapper
11. ✅ Test authentication flow

**Deliverables:**
- ✅ Users can sign up
- ✅ Users can log in
- ✅ JWT tokens work
- ✅ Protected routes require authentication

---

### **Phase 2: Industry Selection & User Context** (Priority: HIGH)
**Duration**: 1-2 days

**Tasks:**
1. ✅ Create industries collection (pre-populate)
2. ✅ Add industry selection to signup
3. ✅ Create industry dropdown component
4. ✅ Update user model with industry
5. ✅ Add industry filter to all queries
6. ✅ Update file upload to include industry
7. ✅ Update agent queries to filter by user + industry

**Deliverables:**
- ✅ Users select industry during signup
- ✅ All data filtered by user + industry
- ✅ Industry-specific file organization

---

### **Phase 3: File Storage Migration** (Priority: HIGH)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Migrate file upload to MongoDB (GridFS or filesystem)
2. ✅ Update file metadata storage
3. ✅ Add user_id to all file operations
4. ✅ Migrate existing files (if any)
5. ✅ Update file retrieval endpoints
6. ✅ Update file list endpoint (filter by user)
7. ✅ Update file delete endpoint
8. ✅ Test file operations with user isolation

**Deliverables:**
- ✅ Files stored per user
- ✅ File metadata in MongoDB
- ✅ User can only see their files

---

### **Phase 4: Vector Store Migration** (Priority: MEDIUM)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Update vector store to be user-specific
2. ✅ Store embeddings in MongoDB (or user-specific ChromaDB)
3. ✅ Update semantic search to filter by user
4. ✅ Update indexing to include user_id
5. ✅ Migrate existing vector stores
6. ✅ Test semantic search with user isolation

**Deliverables:**
- ✅ Vector stores per user
- ✅ Semantic search filtered by user
- ✅ No cross-user data leakage

---

### **Phase 5: Agent & Tools User Context** (Priority: MEDIUM)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Update agent to accept user context
2. ✅ Update all tools to filter by user_id
3. ✅ Update ExcelRetriever to use user files
4. ✅ Update DataCalculator to use user data
5. ✅ Update TrendAnalyzer to use user data
6. ✅ Update ComparativeAnalyzer to use user data
7. ✅ Update KPICalculator to use user data
8. ✅ Update GraphGenerator to use user data
9. ✅ Test all agent queries with user isolation

**Deliverables:**
- ✅ Agent queries user-specific data only
- ✅ All tools respect user boundaries
- ✅ No data leakage between users

---

### **Phase 6: Chat History & Sessions** (Priority: LOW)
**Duration**: 1-2 days

**Tasks:**
1. ✅ Create chat history collection
2. ✅ Store queries and responses
3. ✅ Create chat history endpoint
4. ✅ Create frontend chat history view
5. ✅ Add session management
6. ✅ Test chat history retrieval

**Deliverables:**
- ✅ Chat history stored per user
- ✅ Users can view past queries
- ✅ Session management works

---

### **Phase 7: Frontend Updates** (Priority: MEDIUM)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Create login page
2. ✅ Create signup page
3. ✅ Create industry selection component
4. ✅ Add authentication context provider
5. ✅ Update all pages to require auth
6. ✅ Add user profile dropdown
7. ✅ Add logout functionality
8. ✅ Update navigation for authenticated users
9. ✅ Add loading states
10. ✅ Add error handling

**Deliverables:**
- ✅ Complete authentication UI
- ✅ Protected routes work
- ✅ User can see their data only

---

### **Phase 8: Testing & Security** (Priority: HIGH)
**Duration**: 2-3 days

**Tasks:**
1. ✅ Test user isolation (no cross-user access)
2. ✅ Test authentication (JWT expiration, refresh)
3. ✅ Test file upload/download per user
4. ✅ Test agent queries per user
5. ✅ Security audit (SQL injection, XSS, CSRF)
6. ✅ Password strength validation
7. ✅ Rate limiting on auth endpoints
8. ✅ Input validation
9. ✅ Error handling
10. ✅ Performance testing

**Deliverables:**
- ✅ All security measures in place
- ✅ User isolation verified
- ✅ Performance acceptable

---

## 📦 Dependencies Required

### **Backend Dependencies:**
```txt
# Authentication
python-jose[cryptography]>=3.3.0  # JWT tokens
passlib[bcrypt]>=1.7.4              # Password hashing
python-multipart>=0.0.6              # Form data parsing

# MongoDB
motor>=3.3.0                         # Async MongoDB driver
pymongo>=4.6.0                       # MongoDB driver
pymongo[srv]>=4.6.0                  # MongoDB Atlas support

# Email (optional, for verification)
fastapi-mail>=1.4.0                  # Email sending
```

### **Frontend Dependencies:**
```json
{
  "dependencies": {
    "axios": "^1.6.0",              // HTTP client
    "react-router-dom": "^6.20.0",  // Routing (already installed)
    "js-cookie": "^3.0.5"           // Cookie management (optional)
  }
}
```

---

## 🔒 Security Considerations

### **1. Password Security**
- ✅ Use bcrypt with salt rounds ≥ 12
- ✅ Never store plaintext passwords
- ✅ Enforce password strength (min 8 chars, mix of chars)
- ✅ Rate limit login attempts (prevent brute force)

### **2. JWT Security**
- ✅ Use strong secret key (min 32 chars, random)
- ✅ Set reasonable expiration (15 min access, 7 days refresh)
- ✅ Use HTTPS in production
- ✅ Store tokens securely (httpOnly cookies preferred)

### **3. Data Isolation**
- ✅ Always filter by user_id in queries
- ✅ Never trust client-provided user_id
- ✅ Use middleware to inject user context
- ✅ Test cross-user access attempts

### **4. API Security**
- ✅ Rate limiting on all endpoints
- ✅ Input validation (Pydantic models)
- ✅ CORS properly configured
- ✅ SQL injection prevention (use MongoDB properly)
- ✅ XSS prevention (sanitize inputs)

---

## 🗄️ MongoDB Setup

### **Local Development:**
```bash
# Install MongoDB
brew install mongodb-community  # macOS
# or
sudo apt-get install mongodb    # Linux

# Start MongoDB
brew services start mongodb-community  # macOS
# or
sudo systemctl start mongod            # Linux

# MongoDB will run on: mongodb://localhost:27017
```

### **Production (MongoDB Atlas):**
```bash
# 1. Create account at https://www.mongodb.com/cloud/atlas
# 2. Create cluster (free tier available)
# 3. Get connection string
# 4. Add to .env:
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
```

### **Environment Variables:**
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017/excelllm
MONGODB_DB_NAME=excelllm

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-random
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (update for production)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📝 API Endpoints Design

### **Authentication Endpoints:**
```python
POST   /api/auth/signup          # Create account
POST   /api/auth/login            # Login
POST   /api/auth/logout           # Logout
POST   /api/auth/refresh          # Refresh token
GET    /api/auth/me               # Get current user
PUT    /api/auth/profile          # Update profile
```

### **File Endpoints (Updated):**
```python
POST   /api/files/upload          # Upload file (requires auth)
GET    /api/files/list            # List user's files
GET    /api/files/{file_id}       # Get file metadata
GET    /api/files/{file_id}/data  # Get file data
DELETE /api/files/{file_id}       # Delete file
```

### **Agent Endpoints (Updated):**
```python
POST   /api/agent/query           # Query agent (requires auth)
GET    /api/agent/history         # Get chat history
DELETE /api/agent/history/{id}    # Delete chat entry
```

### **Industry Endpoints:**
```python
GET    /api/industries            # List all industries
GET    /api/industries/{id}       # Get industry details
```

---

## 🎨 Frontend Pages Required

### **1. Authentication Pages:**
- `Login.jsx` - Email/password login
- `Signup.jsx` - Email/password/industry signup
- `ForgotPassword.jsx` - Password reset (optional)

### **2. Protected Pages (Updated):**
- `Dashboard.jsx` - User dashboard (already exists, update)
- `FileUpload.jsx` - Upload files (already exists, update)
- `AgentChat.jsx` - Chat with agent (already exists, update)
- `Visualization.jsx` - View charts (already exists, update)
- `Profile.jsx` - User profile (new)

### **3. Components:**
- `AuthContext.jsx` - Authentication context provider
- `ProtectedRoute.jsx` - Route wrapper for auth
- `IndustrySelector.jsx` - Industry dropdown
- `UserMenu.jsx` - User profile dropdown

---

## 🧪 Testing Strategy

### **1. Unit Tests:**
- ✅ Authentication service
- ✅ User model
- ✅ JWT generation/verification
- ✅ Password hashing

### **2. Integration Tests:**
- ✅ Signup flow
- ✅ Login flow
- ✅ File upload with user context
- ✅ Agent query with user context
- ✅ User isolation (no cross-user access)

### **3. Security Tests:**
- ✅ JWT token expiration
- ✅ Invalid token handling
- ✅ Cross-user access attempts
- ✅ Password strength validation
- ✅ Rate limiting

---

## 📊 Migration Strategy

### **For Existing Data (if any):**
1. **Create migration script** to:
   - Create default "admin" user
   - Assign all existing files to admin user
   - Migrate file metadata to MongoDB
   - Update vector stores with user_id

2. **Run migration:**
   ```bash
   python scripts/migrate_to_mongodb.py
   ```

---

## 🚀 Deployment Considerations

### **1. MongoDB:**
- ✅ Use MongoDB Atlas for production (managed, scalable)
- ✅ Enable authentication
- ✅ Use connection string with credentials
- ✅ Enable backups

### **2. Environment Variables:**
- ✅ Store secrets in environment variables
- ✅ Never commit secrets to git
- ✅ Use different secrets for dev/prod

### **3. CORS:**
- ✅ Update CORS origins for production domain
- ✅ Remove localhost in production

### **4. HTTPS:**
- ✅ Use HTTPS in production
- ✅ Secure cookies (httpOnly, secure, sameSite)

---

## 📋 What I Need From You

### **1. MongoDB Setup:**
- [ ] Do you have MongoDB installed locally?
- [ ] Do you want to use MongoDB Atlas (cloud) or local?
- [ ] If Atlas, do you have an account?

### **2. Industry List:**
- [ ] What industries should be in the dropdown?
  - Suggested: Manufacturing, Retail, Healthcare, Finance, Education, etc.
  - Or should I create a generic list?

### **3. File Storage Preference:**
- [ ] GridFS (MongoDB) or File System?
  - Recommendation: Start with GridFS

### **4. Authentication Details:**
- [ ] Do you want email verification?
- [ ] Do you want password reset functionality?
- [ ] Do you want social login (Google, etc.)?

### **5. User Profile:**
- [ ] What fields in user profile?
  - Name, Company, Phone, etc.?

### **6. Migration:**
- [ ] Do you have existing files to migrate?
- [ ] Should I create a migration script?

---

## ⏱️ Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Auth | 2-3 days | MongoDB setup |
| Phase 2: Industry | 1-2 days | Phase 1 |
| Phase 3: File Storage | 2-3 days | Phase 1, 2 |
| Phase 4: Vector Store | 2-3 days | Phase 3 |
| Phase 5: Agent Context | 2-3 days | Phase 4 |
| Phase 6: Chat History | 1-2 days | Phase 5 |
| Phase 7: Frontend | 2-3 days | Phase 1-6 |
| Phase 8: Testing | 2-3 days | All phases |

**Total**: ~15-22 days (3-4 weeks)

---

## 🎯 Success Criteria

### **Must Have:**
- ✅ Users can sign up with email/password
- ✅ Users can log in
- ✅ Users select industry during signup
- ✅ Files uploaded per user
- ✅ Agent queries user-specific data only
- ✅ No cross-user data access
- ✅ MongoDB stores all data

### **Nice to Have:**
- ✅ Email verification
- ✅ Password reset
- ✅ Chat history
- ✅ User profile management
- ✅ Industry-specific templates

---

## 📝 Next Steps

1. **Review this plan** and provide feedback
2. **Answer questions** in "What I Need From You" section
3. **Set up MongoDB** (local or Atlas)
4. **Start Phase 1** (Authentication)

---

**Ready to begin when you are!** 🚀

