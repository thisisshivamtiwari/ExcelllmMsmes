"""
Tools module for LangChain Agent System.
Provides tools for data retrieval, calculation, analysis, and KPI computation.
"""

from .excel_retriever import ExcelRetriever  # Legacy - for backward compatibility
from .mongodb_excel_retriever import MongoDBExcelRetriever  # MongoDB-aware retriever
from .data_calculator import DataCalculator
from .trend_analyzer import TrendAnalyzer
from .comparative_analyzer import ComparativeAnalyzer
from .kpi_calculator import KPICalculator
from .graph_generator import GraphGenerator

__all__ = [
    "ExcelRetriever",  # Legacy
    "MongoDBExcelRetriever",  # MongoDB-aware
    "DataCalculator",
    "TrendAnalyzer",
    "ComparativeAnalyzer",
    "KPICalculator",
    "GraphGenerator",
]




