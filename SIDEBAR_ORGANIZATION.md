# Sidebar Menu Organization - Phase-wise

## 📋 New Structure

The sidebar is now organized by system phases to reflect the data processing pipeline:

### 🏠 Dashboard
- **Home** - Overview and quick access

### 📊 Phase 1: Data Generation
- **Data Generator** - Generate sample manufacturing data

### 📁 Phase 2: File Management
- **File Upload** - Upload Excel/CSV files for analysis

### 🔍 Phase 4: Semantic Search
- **Semantic Search** - AI-powered column and data search

### 🤖 Phase 5: AI Agent
- **AI Agent Chat** - Natural language query interface with Gemini/Groq

### 🛠️ Development Tools
- **Visualization** - Data visualization tools
- **Question Generator** - Generate test questions
- **LLM Benchmarking** - Benchmark LLM performance
- **Model Optimization** - Prompt engineering and optimization
- **Comparison Analysis** - Compare different approaches

---

## 🎯 Benefits

### 1. **Clear User Journey**
Users can follow the natural workflow:
1. Generate or upload data (Phase 1-2)
2. Search and explore (Phase 4)
3. Query with AI (Phase 5)
4. Use development tools as needed

### 2. **Visual Grouping**
- Section headers in expanded mode
- Visual separators in collapsed mode
- Clear hierarchy

### 3. **Easy Navigation**
- Related features grouped together
- Phases clearly labeled
- Development tools separated

### 4. **Better UX**
- Reduced cognitive load
- Intuitive organization
- Professional appearance

---

## 🔄 Collapsed State

When sidebar is collapsed:
- Section headers hide
- Divider lines separate groups
- Tooltips show full labels
- Icons remain visible

---

## 📝 Notes

### Why Phase 3 is Missing?
Phase 3 (Schema Detection & Relationships) happens automatically in the backend when files are uploaded. No dedicated UI page is needed as:
- Schemas are detected automatically on upload
- Relationships are analyzed in the background
- Results are shown in File Upload page and used by Agent

### Development Tools Section
Groups all testing, benchmarking, and optimization tools together, keeping the main workflow clean and focused on end-user features.

---

## 🎨 Visual Design

```
Dashboard
├── Home                              [FiHome]

Phase 1: Data Generation
├── Data Generator                    [FiDatabase]

Phase 2: File Management
├── File Upload                       [FiUpload]

Phase 4: Semantic Search
├── Semantic Search                   [FiSearch]

Phase 5: AI Agent
├── AI Agent Chat                     [FiMessageCircle]

Development Tools
├── Visualization                     [FiTrendingUp]
├── Question Generator                [FiHelpCircle]
├── LLM Benchmarking                  [FiBarChart2]
├── Model Optimization                [FiCode]
└── Comparison Analysis               [FiLayers]
```

---

## 🚀 Future Enhancements

Potential additions:
- **Phase 3 UI**: Dedicated page for viewing schemas and relationships
- **Reports**: Dashboard for analytics and reports
- **Settings**: System configuration page
- **User Management**: For multi-user deployments
- **Export**: Data export functionality

---

**This organization makes the system more intuitive and professional!** ✨

