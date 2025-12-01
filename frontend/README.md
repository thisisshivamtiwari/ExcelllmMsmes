# ExcelLLM Frontend

React-based web application for ExcelLLM - MSME Manufacturing Analytics Assistant.

## 🚀 Tech Stack

- **Vite** - Fast build tool and dev server
- **React 19** - UI framework
- **Tailwind CSS** - Utility-first CSS framework
- **Recharts** - Chart library for data visualization
- **React Dropzone** - File upload with drag-and-drop
- **Axios** - HTTP client for API calls

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── FileUpload.jsx       # File upload with drag-and-drop
│   │   ├── QueryConsole.jsx     # Natural language query input
│   │   ├── ResultsDisplay.jsx   # Display query results (answer, data, chart, reasoning)
│   │   ├── DataTable.jsx        # Sortable, paginated data table
│   │   ├── ChartRenderer.jsx    # Chart visualization component
│   │   ├── SchemaViewer.jsx     # Display file schemas
│   │   └── QueryHistory.jsx     # Query history sidebar
│   ├── services/
│   │   └── api.js              # API service layer
│   ├── App.jsx                  # Main app component
│   ├── App.css                  # App-specific styles
│   ├── index.css                # Global styles with Tailwind
│   └── main.jsx                 # Entry point
├── public/                      # Static assets
├── index.html                   # HTML template
├── vite.config.js               # Vite configuration
├── tailwind.config.js           # Tailwind configuration
└── package.json                 # Dependencies

```

## 🎨 Features

### 1. File Upload
- Drag-and-drop interface
- Support for `.xlsx`, `.xls`, `.csv` files
- Upload progress tracking
- File list with status indicators

### 2. Query Console
- Natural language query input
- Example queries for guidance
- File selection (optional)
- Loading states

### 3. Results Display
- **Answer Tab**: Textual answer with KPIs
- **Data Tab**: Sortable, paginated data table
- **Chart Tab**: Interactive visualizations (Line, Bar, Pie)
- **Reasoning Tab**: Step-by-step reasoning trace

### 4. Schema Viewer
- View detected schemas for uploaded files
- Column types and descriptions
- Table relationships
- Clean, organized display

### 5. Query History
- Sidebar with recent queries
- Quick access to past results
- Timestamp tracking

## 🛠️ Setup & Development

### Install Dependencies
```bash
npm install
```

### Development Server
```bash
npm run dev
```
Runs on `http://localhost:5173` (default Vite port)

### Build for Production
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## 🔌 API Integration

The frontend expects a backend API at `http://localhost:8000/api` (configurable via `.env`).

### Environment Variables
Create a `.env` file:
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### API Endpoints Expected

1. **POST /api/upload**
   - Upload Excel/CSV files
   - Returns: `{file_id, schema_summary, status}`

2. **POST /api/query**
   - Process natural language query
   - Body: `{query: string, file_ids: string[]}`
   - Returns: `{answer, data, chartSpec, reasoningSteps, kpis}`

3. **GET /api/schema/{fileId}**
   - Get schema for a file
   - Returns: `{tables, columns, relationships}`

4. **GET /api/history**
   - Get query history
   - Returns: `[{query, answer, timestamp}]`

## 🎨 Styling

### Tailwind Configuration
- Custom color palette with `primary` and `manufacturing` colors
- Custom utility classes: `.btn-primary`, `.btn-secondary`, `.card`, `.input-field`

### Component Styling
- Responsive design (desktop-first, tablet-friendly)
- Clean, manufacturing-friendly theme
- Loading states and transitions
- Hover effects and interactive elements

## 📦 Components Overview

### FileUpload
- Drag-and-drop zone
- File validation
- Upload progress
- File list display

### QueryConsole
- Textarea for query input
- Example queries
- File selection
- Submit button with loading state

### ResultsDisplay
- Tabbed interface (Answer, Data, Chart, Reasoning)
- KPI cards display
- Conditional rendering based on available data

### DataTable
- Sortable columns
- Pagination
- Responsive table
- Hover effects

### ChartRenderer
- Supports Line, Bar, Pie charts
- Responsive container
- Tooltips and legends
- Color-coded series

### SchemaViewer
- Table and column display
- Type indicators
- Relationship mapping
- File-based organization

### QueryHistory
- Scrollable list
- Query preview
- Timestamp display
- Click to view details

## 🚧 Current Status

✅ **Completed:**
- All core components
- UI/UX design
- API service layer
- Tailwind styling
- Component structure

⏳ **Pending Backend Integration:**
- Real API calls (currently using mock data)
- File upload to backend
- Query processing
- Schema detection

## 🔄 Next Steps

1. **Backend Integration**: Connect to FastAPI backend when ready
2. **Error Handling**: Add error boundaries and user-friendly error messages
3. **Loading States**: Enhance loading indicators
4. **Responsive Design**: Test and refine mobile/tablet views
5. **Accessibility**: Add ARIA labels and keyboard navigation
6. **Testing**: Add unit and integration tests

## 📝 Notes

- Currently uses mock data for demonstration
- Backend API integration pending
- Chart rendering uses Recharts library
- File upload uses react-dropzone
- All components are functional and ready for backend connection
