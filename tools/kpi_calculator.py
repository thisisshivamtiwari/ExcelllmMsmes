"""
KPI Calculator Tool
Calculates manufacturing KPIs (OEE, FPY, etc.).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class KPICalculator:
    """Calculates manufacturing KPIs."""
    
    def calculate_oee(
        self,
        data: List[Dict[str, Any]],
        availability_column: Optional[str] = None,
        performance_column: Optional[str] = None,
        quality_column: Optional[str] = None,
        planned_production_time_column: Optional[str] = None,
        actual_production_time_column: Optional[str] = None,
        good_units_column: Optional[str] = None,
        total_units_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Overall Equipment Effectiveness (OEE).
        
        OEE = Availability × Performance × Quality
        
        Args:
            data: Production data
            availability_column: Pre-calculated availability (0-1)
            performance_column: Pre-calculated performance (0-1)
            quality_column: Pre-calculated quality (0-1)
            planned_production_time_column: Planned production time
            actual_production_time_column: Actual production time
            good_units_column: Good units produced
            total_units_column: Total units produced
            
        Returns:
            Dictionary with OEE calculation
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            # If pre-calculated components provided
            if availability_column and performance_column and quality_column:
                if all(col in df.columns for col in [availability_column, performance_column, quality_column]):
                    df['availability'] = pd.to_numeric(df[availability_column], errors='coerce')
                    df['performance'] = pd.to_numeric(df[performance_column], errors='coerce')
                    df['quality'] = pd.to_numeric(df[quality_column], errors='coerce')
                else:
                    return {
                        "success": False,
                        "error": "Required columns not found for pre-calculated OEE"
                    }
            else:
                # Calculate components
                availability = 1.0
                performance = 1.0
                quality = 1.0
                
                # Calculate Availability
                if planned_production_time_column and actual_production_time_column:
                    if all(col in df.columns for col in [planned_production_time_column, actual_production_time_column]):
                        planned = pd.to_numeric(df[planned_production_time_column], errors='coerce').sum()
                        actual = pd.to_numeric(df[actual_production_time_column], errors='coerce').sum()
                        availability = (actual / planned) if planned > 0 else 0
                
                # Calculate Performance (simplified - would need ideal cycle time)
                # For now, assume performance = 1 if not provided
                
                # Calculate Quality
                if good_units_column and total_units_column:
                    if all(col in df.columns for col in [good_units_column, total_units_column]):
                        good = pd.to_numeric(df[good_units_column], errors='coerce').sum()
                        total = pd.to_numeric(df[total_units_column], errors='coerce').sum()
                        quality = (good / total) if total > 0 else 0
                
                df['availability'] = availability
                df['performance'] = performance
                df['quality'] = quality
            
            # Calculate OEE
            df['oee'] = df['availability'] * df['performance'] * df['quality']
            
            avg_oee = df['oee'].mean()
            avg_availability = df['availability'].mean()
            avg_performance = df['performance'].mean()
            avg_quality = df['quality'].mean()
            
            return {
                "success": True,
                "kpi": "OEE",
                "oee": float(avg_oee) if pd.notna(avg_oee) else None,
                "availability": float(avg_availability) if pd.notna(avg_availability) else None,
                "performance": float(avg_performance) if pd.notna(avg_performance) else None,
                "quality": float(avg_quality) if pd.notna(avg_quality) else None,
                "oee_percentage": float(avg_oee * 100) if pd.notna(avg_oee) else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating OEE: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_fpy(
        self,
        data: List[Dict[str, Any]],
        good_units_column: str,
        total_units_column: str
    ) -> Dict[str, Any]:
        """
        Calculate First Pass Yield (FPY).
        
        FPY = Good Units / Total Units
        
        Args:
            data: Production data
            good_units_column: Column with good units
            total_units_column: Column with total units
            
        Returns:
            Dictionary with FPY calculation
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if good_units_column not in df.columns or total_units_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Required columns not found: {good_units_column}, {total_units_column}"
                }
            
            good = pd.to_numeric(df[good_units_column], errors='coerce').sum()
            total = pd.to_numeric(df[total_units_column], errors='coerce').sum()
            
            fpy = (good / total) if total > 0 else 0
            
            return {
                "success": True,
                "kpi": "FPY",
                "fpy": float(fpy),
                "fpy_percentage": float(fpy * 100),
                "good_units": float(good),
                "total_units": float(total),
                "defect_units": float(total - good)
            }
            
        except Exception as e:
            logger.error(f"Error calculating FPY: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_defect_rate(
        self,
        data: List[Dict[str, Any]],
        defect_column: str,
        total_column: str
    ) -> Dict[str, Any]:
        """
        Calculate defect rate.
        
        Defect Rate = Defects / Total
        
        Args:
            data: Quality data
            defect_column: Column with defect count
            total_column: Column with total count
            
        Returns:
            Dictionary with defect rate calculation
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            if defect_column not in df.columns or total_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Required columns not found: {defect_column}, {total_column}"
                }
            
            defects = pd.to_numeric(df[defect_column], errors='coerce').sum()
            total = pd.to_numeric(df[total_column], errors='coerce').sum()
            
            defect_rate = (defects / total) if total > 0 else 0
            
            return {
                "success": True,
                "kpi": "Defect Rate",
                "defect_rate": float(defect_rate),
                "defect_rate_percentage": float(defect_rate * 100),
                "defects": float(defects),
                "total": float(total),
                "good": float(total - defects)
            }
            
        except Exception as e:
            logger.error(f"Error calculating defect rate: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }




