"""
MongoDB-based Deterministic Tools for Agent System
All tools return canonical envelope format with provenance
"""

import time
import json
import ast
import operator as op
from decimal import Decimal, getcontext
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import os

# High precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

# Allowed operations for calc_eval
ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv
}


def now_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)


def get_sync_mongo_client():
    """Get synchronous MongoDB client for tools (pymongo)"""
    from pymongo import MongoClient
    import os
    
    uri = os.getenv("MONGODB_URI")
    if uri:
        client = MongoClient(uri)
        # Extract database name from URI
        uri_parts = uri.split("?")[0]
        if "/" in uri_parts:
            db_name_from_uri = uri_parts.split("/")[-1]
            if db_name_from_uri and db_name_from_uri not in ["", "mongodb+srv:", "mongodb:"]:
                db_name = db_name_from_uri
            else:
                db_name = os.getenv("MONGODB_DB_NAME", "excelllm")
        else:
            db_name = os.getenv("MONGODB_DB_NAME", "excelllm")
        return client[db_name]
    
    host = os.getenv("MONGODB_HOST", "localhost")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    db_name = os.getenv("MONGODB_DB_NAME", "excelllm")
    
    return MongoClient(f"mongodb://{host}:{port}")[db_name]


def get_date_range(
    user_id: str,
    file_id: str,
    table_name: str,
    time_col: str
) -> Dict[str, Any]:
    """
    Get date range information for a time column.
    Used to detect if data is too large and needs date filtering.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        time_col: Time column name
    
    Returns:
        Canonical tool envelope with min/max dates and row count
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        # Build match stage
        match_stage = {
            "$match": {
                "user_id": user_id_obj,
                "file_id": file_id,
                "table_name": table_name,
                f"row.{time_col}": {"$exists": True, "$ne": None}
            }
        }
        
        # Convert string dates to date objects
        date_conversion = {
            "$cond": {
                "if": {"$eq": [{"$type": f"$row.{time_col}"}, "string"]},
                "then": {
                    "$dateFromString": {
                        "dateString": f"$row.{time_col}",
                        "onError": None,
                        "onNull": None
                    }
                },
                "else": f"$row.{time_col}"
            }
        }
        
        # Get min/max dates and count
        pipeline = [
            match_stage,
            {"$addFields": {"_date_converted": date_conversion}},
            {"$match": {"_date_converted": {"$ne": None}}},
            {
                "$group": {
                    "_id": None,
                    "min_date": {"$min": "$_date_converted"},
                    "max_date": {"$max": "$_date_converted"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        res = list(coll.aggregate(pipeline))
        
        if res and res[0]:
            result_doc = res[0]
            min_date = result_doc.get("min_date")
            max_date = result_doc.get("max_date")
            count = result_doc.get("count", 0)
            
            # Calculate date range span in days
            span_days = None
            if min_date and max_date:
                if isinstance(min_date, datetime) and isinstance(max_date, datetime):
                    span_days = (max_date - min_date).days
                elif isinstance(min_date, str) and isinstance(max_date, str):
                    try:
                        from datetime import datetime as dt
                        min_dt = dt.fromisoformat(min_date.replace('Z', '+00:00'))
                        max_dt = dt.fromisoformat(max_date.replace('Z', '+00:00'))
                        span_days = (max_dt - min_dt).days
                    except:
                        pass
            
            return {
                "ok": True,
                "tool": "get_date_range",
                "result": {
                    "min_date": min_date.isoformat() if isinstance(min_date, datetime) else str(min_date) if min_date else None,
                    "max_date": max_date.isoformat() if isinstance(max_date, datetime) else str(max_date) if max_date else None,
                    "row_count": count,
                    "span_days": span_days
                },
                "unit": None,
                "provenance": {
                    "mongo_pipeline": pipeline,
                    "time_column": time_col
                },
                "meta": {"time_ms": now_ms() - start_ms}
            }
        else:
            return {
                "ok": False,
                "tool": "get_date_range",
                "error": "no_data_found",
                "result": None,
                "unit": None,
                "provenance": None,
                "meta": {"time_ms": now_ms() - start_ms}
            }
    except Exception as e:
        logger.error(f"Error in get_date_range: {str(e)}")
        return {
            "ok": False,
            "tool": "get_date_range",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def table_loader(
    user_id: str,
    file_id: str,
    table_name: str,
    filters: Optional[Dict] = None,
    fields: Optional[List[str]] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Load table sample and schema from MongoDB tables collection.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        filters: Optional MongoDB filter dict
        fields: Optional list of fields to project
        limit: Maximum rows to return
    
    Returns:
        Canonical tool envelope with schema, sample rows, and provenance
    """
    start_ms = now_ms()
    
    try:
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Build query - convert user_id to ObjectId if it's a string
        from bson import ObjectId
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        query = {
            "user_id": user_id_obj,
            "file_id": file_id,
            "table_name": table_name
        }
        
        if filters:
            query.update(filters)
        
        # Projection
        projection = None
        if fields:
            projection = {f: 1 for f in fields}
            projection["_id"] = 0
        
        # Fetch sample rows
        cursor = coll.find(query, projection=projection).limit(limit)
        rows = list(cursor)
        
        if not rows:
            return {
                "ok": False,
                "tool": "table_loader",
                "error": "no_rows",
                "result": None,
                "unit": None,
                "provenance": {
                    "mongo_query": query,
                    "matched_row_count": 0,
                    "sample_rows": []
                },
                "meta": {"time_ms": now_ms() - start_ms}
            }
        
        # Deduce schema from first row
        sample = rows[:5]
        schema = {}
        if sample:
            for key, value in sample[0].items():
                if key not in ["_id", "user_id", "file_id", "table_name"]:
                    schema[key] = type(value).__name__
        
        # Get matched count
        matched_count = coll.count_documents(query)
        
        return {
            "ok": True,
            "tool": "table_loader",
            "result": {
                "schema": schema,
                "sample_rows": sample,
                "row_count": matched_count
            },
            "unit": None,
            "provenance": {
                "mongo_query": query,
                "matched_row_count": matched_count,
                "sample_rows": sample[:5]
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in table_loader: {str(e)}")
        return {
            "ok": False,
            "tool": "table_loader",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def agg_helper(
    user_id: str,
    file_id: str,
    table_name: str,
    filters: Optional[Dict] = None,
    metrics: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Run deterministic aggregations using MongoDB aggregation pipeline.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        filters: Optional MongoDB filter dict
        metrics: List of metric operations, e.g.:
            [{"op": "sum", "col": "revenue", "alias": "total_revenue"}]
    
    Returns:
        Canonical tool envelope with aggregated results and provenance
    """
    start_ms = now_ms()
    
    try:
        db = get_sync_mongo_client()
        coll = db['tables']
        
        if not metrics:
            return {
                "ok": False,
                "tool": "agg_helper",
                "error": "no_metrics_provided",
                "result": None,
                "unit": None,
                "provenance": None,
                "meta": {"time_ms": now_ms() - start_ms}
            }
        
        # Build match stage - convert user_id to ObjectId if needed
        from bson import ObjectId
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        match_stage = {
            "$match": {
                "user_id": user_id_obj,
                "file_id": file_id,
                "table_name": table_name
            }
        }
        
        if filters:
            # Convert filter format to MongoDB query format
            if isinstance(filters, list):
                # Handle list of filter objects like [{"col":"Line_Machine","op":"starts_with","value":"Line-1"}]
                for filter_obj in filters:
                    if isinstance(filter_obj, dict):
                        col = filter_obj.get("col", "")
                        op = filter_obj.get("op", "").lower()
                        value = filter_obj.get("value")
                        
                        if col and value is not None:
                            col_path = f"row.{col}"
                            if op == "starts_with" or op == "startswith":
                                match_stage["$match"][col_path] = {"$regex": f"^{value}", "$options": "i"}
                            elif op == "ends_with" or op == "endswith":
                                match_stage["$match"][col_path] = {"$regex": f"{value}$", "$options": "i"}
                            elif op == "contains":
                                match_stage["$match"][col_path] = {"$regex": value, "$options": "i"}
                            elif op == "eq" or op == "equals" or op == "==":
                                match_stage["$match"][col_path] = value
                            elif op == "ne" or op == "not_equals" or op == "!=":
                                match_stage["$match"][col_path] = {"$ne": value}
                            elif op == "gt" or op == "greater_than" or op == ">":
                                match_stage["$match"][col_path] = {"$gt": value}
                            elif op == "gte" or op == "greater_than_equal" or op == ">=":
                                match_stage["$match"][col_path] = {"$gte": value}
                            elif op == "lt" or op == "less_than" or op == "<":
                                match_stage["$match"][col_path] = {"$lt": value}
                            elif op == "lte" or op == "less_than_equal" or op == "<=":
                                match_stage["$match"][col_path] = {"$lte": value}
                            elif op == "in":
                                match_stage["$match"][col_path] = {"$in": value if isinstance(value, list) else [value]}
                            else:
                                # Default to equality
                                match_stage["$match"][col_path] = value
            elif isinstance(filters, dict):
                # Handle direct MongoDB filter dict
                match_stage["$match"].update(filters)
        
        # Build group stage
        group_stage = {"$group": {"_id": None}}
        
        for m in metrics:
            op_name = m.get('op', '').lower()
            col = m.get('col', '')
            alias = m.get('alias', f"{op_name}_{col}")
            
            if not col:
                continue
            
            # Access column via row.field_name structure
            col_path = f"$row.{col}"
            
            if op_name == "sum":
                group_stage["$group"][alias] = {"$sum": col_path}
            elif op_name == "avg":
                group_stage["$group"][alias] = {"$avg": col_path}
            elif op_name == "min":
                group_stage["$group"][alias] = {"$min": col_path}
            elif op_name == "max":
                group_stage["$group"][alias] = {"$max": col_path}
            elif op_name == "count":
                group_stage["$group"][alias] = {"$sum": 1}
            elif op_name == "median":
                # Use $percentile if available (MongoDB 5.2+), else compute in Python
                group_stage["$group"][alias] = {"$percentile": {
                    "input": col_path,
                    "p": [0.5],
                    "method": "approximate"
                }}
            else:
                logger.warning(f"Unsupported operation: {op_name}")
                continue
        
        # Execute pipeline
        pipeline = [match_stage, group_stage]
        agg_res = list(coll.aggregate(pipeline))
        
        result = agg_res[0] if agg_res else {}
        
        # Convert numeric fields to Decimal for accuracy
        for key in list(result.keys()):
            if key == "_id":
                continue
            value = result[key]
            if isinstance(value, (int, float, np.number)):
                result[key] = Decimal(str(value))
            elif isinstance(value, list) and len(value) == 1:
                # Handle percentile result
                result[key] = Decimal(str(value[0]))
        
        # Get sample rows for provenance
        sample_rows = list(coll.find(match_stage["$match"]).limit(5))
        matched_count = coll.count_documents(match_stage["$match"])
        
        return {
            "ok": True,
            "tool": "agg_helper",
            "result": result,
            "unit": None,
            "provenance": {
                "mongo_pipeline": pipeline,
                "matched_row_count": matched_count,
                "sample_rows": sample_rows[:3]
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in agg_helper: {str(e)}")
        return {
            "ok": False,
            "tool": "agg_helper",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def timeseries_analyzer(
    user_id: str,
    file_id: str,
    table_name: str,
    time_col: str,
    metric_col: str,
    freq: str = "month",
    agg: str = "sum",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Compute time-bucketed series using MongoDB dateTrunc and return slope/trend.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        time_col: Time column name
        metric_col: Metric column to aggregate
        freq: Frequency ("day", "week", "month", "year")
        agg: Aggregation operation ("sum", "avg", "count", "min", "max")
        start: Optional start date
        end: Optional end date
    
    Returns:
        Canonical tool envelope with time series and trend slope
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        # Build match stage
        match_stage = {
            "$match": {
                "user_id": user_id_obj,
                "file_id": file_id,
                "table_name": table_name,
                f"row.{time_col}": {"$exists": True, "$ne": None},
                f"row.{metric_col}": {"$exists": True, "$ne": None}
            }
        }
        
        if start or end:
            time_filter = {}
            if start:
                time_filter["$gte"] = start
            if end:
                time_filter["$lte"] = end
            match_stage["$match"][f"row.{time_col}"] = time_filter
        
        # Convert string dates to date objects first, then truncate
        # Handle both string dates (like "2025-11-02") and date objects
        # Use $dateFromString to convert ISO date strings to date objects
        date_conversion = {
            "$cond": {
                "if": {"$eq": [{"$type": f"$row.{time_col}"}, "string"]},
                "then": {
                    "$dateFromString": {
                        "dateString": f"$row.{time_col}",
                        "onError": None,
                        "onNull": None
                    }
                },
                "else": f"$row.{time_col}"
            }
        }
        
        # Build date truncation - use $dateTrunc if date conversion succeeds, else use $dateToString
        date_bucket_trunc = {
            "$dateTrunc": {
                "date": "$_date_converted",
                "unit": freq
            }
        }
        
        # Fallback format for string-based grouping if date conversion fails
        date_format_map = {
            "day": "%Y-%m-%d",
            "week": "%Y-W%V",
            "month": "%Y-%m",
            "year": "%Y"
        }
        date_format = date_format_map.get(freq, "%Y-%m-%d")
        
        date_bucket = {
            "$cond": {
                "if": {"$ne": ["$_date_converted", None]},
                "then": date_bucket_trunc,
                "else": {
                    "$dateToString": {
                        "format": date_format,
                        "date": {
                            "$dateFromString": {
                                "dateString": f"$row.{time_col}",
                                "onError": None
                            }
                        }
                    }
                }
            }
        }
        
        # Build aggregation pipeline
        pipeline = [
            match_stage,
            {"$addFields": {"_date_converted": date_conversion}},
            {"$match": {"_date_converted": {"$ne": None}}},
            {"$addFields": {"_period": date_bucket}},
            {
                "$group": {
                    "_id": "$_period",
                    "value": {f"${agg}": f"$row.{metric_col}"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        res = list(coll.aggregate(pipeline))
        
        # Convert to series format
        series = []
        for r in res:
            period = r["_id"]
            value = r.get("value")
            series.append({
                "period": period.isoformat() if isinstance(period, datetime) else str(period),
                "value": Decimal(str(value)) if value is not None else None
            })
        
        # Compute slope deterministically using numpy
        slope = Decimal("0")
        if len(series) >= 2:
            xs = np.arange(len(series))
            ys = np.array([
                float(s["value"]) if s["value"] is not None else 0.0
                for s in series
            ])
            if len(ys) > 0 and np.any(ys != 0):
                slope_coeffs = np.polyfit(xs, ys, 1)
                slope = Decimal(str(slope_coeffs[0]))
        
        matched_count = coll.count_documents(match_stage["$match"])
        
        return {
            "ok": True,
            "tool": "timeseries_analyzer",
            "result": {
                "series": series,
                "slope": slope,
                "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
            },
            "unit": None,
            "provenance": {
                "mongo_pipeline": pipeline,
                "matched_row_count": matched_count
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in timeseries_analyzer: {str(e)}")
        return {
            "ok": False,
            "tool": "timeseries_analyzer",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def compare_entities(
    user_id: str,
    file_id: str,
    table_name: str,
    key_col: str,
    metric_col: str,
    entity_a: str,
    entity_b: str,
    agg: str = "sum",
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Compare two entities side-by-side with percent difference.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        key_col: Entity identifier column
        metric_col: Metric column to aggregate
        entity_a: First entity value
        entity_b: Second entity value
        agg: Aggregation operation ("sum", "avg", "count", "min", "max")
        filters: Optional additional filters
    
    Returns:
        Canonical tool envelope with comparison results
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Build match stages for each entity - convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        base_match = {
            "user_id": user_id_obj,
            "file_id": file_id,
            "table_name": table_name,
            f"row.{key_col}": {"$exists": True},
            f"row.{metric_col}": {"$exists": True, "$ne": None}
        }
        
        if filters:
            if isinstance(filters, dict):
                base_match.update(filters)
            elif isinstance(filters, list):
                # Convert filter format to MongoDB query format
                for filter_obj in filters:
                    if isinstance(filter_obj, dict):
                        col = filter_obj.get("col", "")
                        op = filter_obj.get("op", "").lower()
                        value = filter_obj.get("value")
                        
                        if col and value is not None:
                            col_path = f"row.{col}"
                            if op == "starts_with" or op == "startswith":
                                base_match[col_path] = {"$regex": f"^{value}", "$options": "i"}
                            elif op == "eq" or op == "equals" or op == "==":
                                base_match[col_path] = value
                            else:
                                base_match[col_path] = value
        
        # Support partial matching for entity values (e.g., "Line-1" matches "Line-1/Machine-M1")
        # Use regex for partial matching
        match_a = {**base_match, f"row.{key_col}": {"$regex": f"^{entity_a}", "$options": "i"}}
        match_b = {**base_match, f"row.{key_col}": {"$regex": f"^{entity_b}", "$options": "i"}}
        
        # Aggregate for entity A
        pipeline_a = [
            {"$match": match_a},
            {
                "$group": {
                    "_id": None,
                    "value": {f"${agg}": f"$row.{metric_col}"}
                }
            }
        ]
        res_a = list(coll.aggregate(pipeline_a))
        value_a = Decimal(str(res_a[0]["value"])) if res_a and res_a[0].get("value") is not None else Decimal("0")
        
        # Aggregate for entity B
        pipeline_b = [
            {"$match": match_b},
            {
                "$group": {
                    "_id": None,
                    "value": {f"${agg}": f"$row.{metric_col}"}
                }
            }
        ]
        res_b = list(coll.aggregate(pipeline_b))
        value_b = Decimal(str(res_b[0]["value"])) if res_b and res_b[0].get("value") is not None else Decimal("0")
        
        # Calculate percent difference
        if value_b != 0:
            percent_diff = ((value_a - value_b) / value_b) * 100
        else:
            percent_diff = Decimal("0") if value_a == 0 else Decimal("inf")
        
        return {
            "ok": True,
            "tool": "compare_entities",
            "result": {
                entity_a: float(value_a),
                entity_b: float(value_b),
                "difference": float(value_a - value_b),
                "percent_difference": float(percent_diff)
            },
            "unit": None,
            "provenance": {
                "entity_a_pipeline": pipeline_a,
                "entity_b_pipeline": pipeline_b,
                "matched_a_count": coll.count_documents(match_a),
                "matched_b_count": coll.count_documents(match_b)
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in compare_entities: {str(e)}")
        return {
            "ok": False,
            "tool": "compare_entities",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def calc_eval(expr: str) -> Dict[str, Any]:
    """
    Safe deterministic calculator using Decimal and AST parsing.
    Only allows numbers and basic arithmetic operations.
    
    Args:
        expr: Mathematical expression string
    
    Returns:
        Canonical tool envelope with calculated value
    """
    start_ms = now_ms()
    
    try:
        def _eval(node):
            if isinstance(node, ast.Constant):
                return Decimal(str(node.value))
            if isinstance(node, ast.Num):  # Python < 3.8
                return Decimal(str(node.n))
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                op_type = type(node.op)
                if op_type not in ALLOWED_OPS:
                    raise ValueError(f"Unsupported operation: {op_type}")
                return ALLOWED_OPS[op_type](left, right)
            if isinstance(node, ast.UnaryOp):
                return ALLOWED_OPS[type(node.op)](_eval(node.operand))
            raise ValueError(f"Unsupported node type: {type(node)}")
        
        # Parse and evaluate
        tree = ast.parse(expr, mode='eval')
        value = _eval(tree.body)
        
        return {
            "ok": True,
            "tool": "calc_eval",
            "result": {"value": float(value), "decimal_value": str(value)},
            "unit": None,
            "provenance": {"expression": expr},
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in calc_eval: {str(e)}")
        return {
            "ok": False,
            "tool": "calc_eval",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def statistical_summary(
    user_id: str,
    file_id: str,
    table_name: str,
    columns: List[str],
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Compute statistical summary (min/max/mean/median/std) for numeric columns.
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        columns: List of column names to summarize
        filters: Optional MongoDB filter dict
    
    Returns:
        Canonical tool envelope with statistical summaries
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        match_stage = {
            "$match": {
                "user_id": user_id_obj,
                "file_id": file_id,
                "table_name": table_name
            }
        }
        
        if filters:
            match_stage["$match"].update(filters)
        
        # Build group stage with all statistics
        group_stage = {"$group": {"_id": None}}
        
        for col in columns:
            col_path = f"$row.{col}"
            group_stage["$group"][f"{col}_min"] = {"$min": col_path}
            group_stage["$group"][f"{col}_max"] = {"$max": col_path}
            group_stage["$group"][f"{col}_avg"] = {"$avg": col_path}
            group_stage["$group"][f"{col}_std"] = {"$stdDevPop": col_path}
            group_stage["$group"][f"{col}_median"] = {"$percentile": {
                "input": col_path,
                "p": [0.5],
                "method": "approximate"
            }}
        
        pipeline = [match_stage, group_stage]
        res = list(coll.aggregate(pipeline))
        
        result = {}
        if res:
            stats = res[0]
            for col in columns:
                result[col] = {
                    "min": float(stats.get(f"{col}_min", 0)) if stats.get(f"{col}_min") is not None else None,
                    "max": float(stats.get(f"{col}_max", 0)) if stats.get(f"{col}_max") is not None else None,
                    "mean": float(stats.get(f"{col}_avg", 0)) if stats.get(f"{col}_avg") is not None else None,
                    "std": float(stats.get(f"{col}_std", 0)) if stats.get(f"{col}_std") is not None else None,
                    "median": float(stats.get(f"{col}_median", [0])[0]) if isinstance(stats.get(f"{col}_median"), list) else None
                }
        
        matched_count = coll.count_documents(match_stage["$match"])
        
        return {
            "ok": True,
            "tool": "statistical_summary",
            "result": result,
            "unit": None,
            "provenance": {
                "mongo_pipeline": pipeline,
                "matched_row_count": matched_count
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in statistical_summary: {str(e)}")
        return {
            "ok": False,
            "tool": "statistical_summary",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def rank_entities(
    user_id: str,
    file_id: str,
    table_name: str,
    key_col: str,
    metric_col: str,
    agg: str = "sum",
    n: int = 5,
    order: str = "desc",
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Rank entities by aggregated metric (top N or bottom N).
    
    Args:
        user_id: User ID for multi-tenant filtering
        file_id: File ID
        table_name: Table/sheet name
        key_col: Entity identifier column (e.g., "Product", "Material_Name")
        metric_col: Metric column to aggregate (e.g., "Sales", "Consumption_Kg")
        agg: Aggregation operation ("sum", "avg", "count", "min", "max")
        n: Number of top/bottom entities to return
        order: "desc" for top N (highest), "asc" for bottom N (lowest)
        filters: Optional additional filters
    
    Returns:
        Canonical tool envelope with ranked entities and their values
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        coll = db['tables']
        
        # Convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        # Build match stage
        match_stage = {
            "$match": {
                "user_id": user_id_obj,
                "file_id": file_id,
                "table_name": table_name,
                f"row.{key_col}": {"$exists": True, "$ne": None},
                f"row.{metric_col}": {"$exists": True, "$ne": None}
            }
        }
        
        if filters:
            if isinstance(filters, dict):
                match_stage["$match"].update(filters)
            elif isinstance(filters, list):
                # Convert filter format to MongoDB query format
                for filter_obj in filters:
                    if isinstance(filter_obj, dict):
                        col = filter_obj.get("col", "")
                        op = filter_obj.get("op", "").lower()
                        value = filter_obj.get("value")
                        
                        if col and value is not None:
                            col_path = f"row.{col}"
                            if op == "starts_with" or op == "startswith":
                                match_stage["$match"][col_path] = {"$regex": f"^{value}", "$options": "i"}
                            elif op == "eq" or op == "equals" or op == "==":
                                match_stage["$match"][col_path] = value
                            else:
                                match_stage["$match"][col_path] = value
        
        # Build aggregation pipeline
        sort_order = -1 if order.lower() == "desc" else 1
        
        # Handle "count" aggregation specially - count documents, not sum a metric
        if agg.lower() == "count":
            # For count, we don't need metric_col - just count documents per entity
            # Remove metric_col requirement from match stage
            if f"row.{metric_col}" in match_stage["$match"]:
                del match_stage["$match"][f"row.{metric_col}"]
            
            group_stage = {
                "$group": {
                    "_id": f"$row.{key_col}",
                    "value": {"$sum": 1}  # Count documents in each group
                }
            }
        else:
            # For other aggregations (sum, avg, min, max), use the metric column
            group_stage = {
                "$group": {
                    "_id": f"$row.{key_col}",
                    "value": {f"${agg}": f"$row.{metric_col}"}
                }
            }
        
        pipeline = [
            match_stage,
            group_stage,
            {"$sort": {"value": sort_order}},
            {"$limit": n}
        ]
        
        res = list(coll.aggregate(pipeline))
        
        # Format results
        ranked_entities = []
        for r in res:
            entity_name = r.get("_id", "")
            value = r.get("value")
            ranked_entities.append({
                "entity": str(entity_name),
                "value": Decimal(str(value)) if value is not None else Decimal("0")
            })
        
        matched_count = coll.count_documents(match_stage["$match"])
        
        return {
            "ok": True,
            "tool": "rank_entities",
            "result": {
                "entities": ranked_entities,
                "count": len(ranked_entities),
                "metric": metric_col,
                "aggregation": agg,
                "order": order
            },
            "unit": None,
            "provenance": {
                "mongo_pipeline": pipeline,
                "matched_row_count": matched_count
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in rank_entities: {str(e)}")
        return {
            "ok": False,
            "tool": "rank_entities",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }


def list_user_files(user_id: str) -> Dict[str, Any]:
    """
    List all files available for the user.
    
    Args:
        user_id: User ID for multi-tenant filtering
    
    Returns:
        Canonical tool envelope with list of files and their metadata
    """
    start_ms = now_ms()
    
    try:
        from bson import ObjectId
        db = get_sync_mongo_client()
        files_collection = db['files']
        
        # Convert user_id to ObjectId if needed
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
        except:
            user_id_obj = user_id
        
        # Get all files for user
        files = list(files_collection.find(
            {"user_id": user_id_obj},
            {"file_id": 1, "original_filename": 1, "file_type": 1, "metadata": 1, "_id": 0}
        ))
        
        # Format file list
        file_list = []
        for file_doc in files:
            metadata = file_doc.get("metadata", {})
            sheets = metadata.get("sheets", {})
            file_list.append({
                "file_id": file_doc.get("file_id"),
                "filename": file_doc.get("original_filename"),
                "file_type": file_doc.get("file_type"),
                "table_names": list(sheets.keys()) if sheets else ["Sheet1"],
                "row_count": sum(sheet.get("row_count", 0) for sheet in sheets.values()) if sheets else 0
            })
        
        return {
            "ok": True,
            "tool": "list_user_files",
            "result": {
                "files": file_list,
                "count": len(file_list)
            },
            "unit": None,
            "provenance": {
                "user_id": str(user_id_obj),
                "matched_files": len(file_list)
            },
            "meta": {"time_ms": now_ms() - start_ms}
        }
    except Exception as e:
        logger.error(f"Error in list_user_files: {str(e)}")
        return {
            "ok": False,
            "tool": "list_user_files",
            "error": str(e),
            "result": None,
            "unit": None,
            "provenance": None,
            "meta": {"time_ms": now_ms() - start_ms}
        }

