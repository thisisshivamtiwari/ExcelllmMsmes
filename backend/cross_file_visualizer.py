"""
Cross-File Relationship Visualizer
Creates relationship graphs and charts for multiple selected files using Gemini API and existing tools
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CrossFileVisualizer:
    """Generates visualizations for cross-file relationships"""
    
    def __init__(self):
        """Initialize cross-file visualizer"""
        logger.info("CrossFileVisualizer initialized")
    
    def create_relationship_graph(self, relationships: List[Dict[str, Any]], file_ids: List[str]) -> Dict[str, Any]:
        """
        Create a network graph structure from relationships
        
        Args:
            relationships: List of relationship dictionaries
            file_ids: List of selected file IDs
            
        Returns:
            Graph structure with nodes and edges
        """
        nodes = []
        edges = []
        node_map = {}
        
        # Create nodes for files
        for file_id in file_ids:
            node_id = f"file_{file_id}"
            if node_id not in node_map:
                node_map[node_id] = len(nodes)
                nodes.append({
                    "id": node_id,
                    "label": f"File: {file_id[:8]}...",
                    "type": "file",
                    "file_id": file_id,
                    "size": 30
                })
        
        # Process relationships to create nodes and edges
        for rel in relationships:
            source_col = rel.get("source_column", rel.get("column", ""))
            target_col = rel.get("target_column", "")
            rel_type = rel.get("type", "unknown")
            strength = rel.get("strength", "medium")
            impact = rel.get("impact", "informational")
            
            if not source_col or not target_col:
                continue
            
            # Extract file IDs from column names (format: file_id::sheet::column)
            source_parts = source_col.split("::")
            target_parts = target_col.split("::")
            
            if len(source_parts) >= 3 and len(target_parts) >= 3:
                source_file_id = source_parts[0]
                target_file_id = target_parts[0]
                
                # Only include relationships between selected files
                if source_file_id not in file_ids or target_file_id not in file_ids:
                    continue
                
                source_col_name = source_parts[-1]
                target_col_name = target_parts[-1]
                
                # Create column nodes
                source_node_id = f"{source_file_id}_{source_col_name}"
                target_node_id = f"{target_file_id}_{target_col_name}"
                
                if source_node_id not in node_map:
                    node_map[source_node_id] = len(nodes)
                    nodes.append({
                        "id": source_node_id,
                        "label": source_col_name,
                        "type": "column",
                        "file_id": source_file_id,
                        "size": 20
                    })
                
                if target_node_id not in node_map:
                    node_map[target_node_id] = len(nodes)
                    nodes.append({
                        "id": target_node_id,
                        "label": target_col_name,
                        "type": "column",
                        "file_id": target_file_id,
                        "size": 20
                    })
                
                # Create edge
                edge_weight = {"strong": 3, "medium": 2, "weak": 1}.get(strength, 2)
                edge_color = {
                    "critical": "#EF4444",
                    "important": "#F59E0B",
                    "informational": "#3B82F6"
                }.get(impact, "#3B82F6")
                
                edges.append({
                    "source": source_node_id,
                    "target": target_node_id,
                    "type": rel_type,
                    "strength": strength,
                    "impact": impact,
                    "weight": edge_weight,
                    "color": edge_color,
                    "label": rel_type
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def create_cross_file_charts(self, relationships: List[Dict[str, Any]], file_ids: List[str], file_metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create charts based on cross-file relationships
        
        Args:
            relationships: List of relationship dictionaries
            file_ids: List of selected file IDs
            file_metadata: Dictionary mapping file_id to file metadata
            
        Returns:
            List of chart configurations
        """
        charts = []
        
        # Create a set of filenames for selected files (relationships use filenames, not file_ids)
        selected_filenames = set()
        file_id_to_filename = {}
        for file_id in file_ids:
            metadata = file_metadata.get(file_id, {})
            filename = metadata.get("original_filename", "")
            if filename:
                selected_filenames.add(filename)
                # Also add without extension
                filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                selected_filenames.add(filename_no_ext)
                file_id_to_filename[file_id] = filename
                file_id_to_filename[filename] = file_id
                file_id_to_filename[filename_no_ext] = file_id
        
        # Filter to only cross-file relationships (relationships use filenames in columns)
        cross_file_rels = []
        for rel in relationships:
            source_col = rel.get("source_column", rel.get("column", ""))
            target_col = rel.get("target_column", "")
            
            if source_col and target_col:
                # Extract filename from column format: filename::sheet::column
                source_filename = None
                target_filename = None
                
                if "::" in source_col:
                    parts = source_col.split("::")
                    if len(parts) >= 1:
                        source_filename = parts[0]
                        # Remove extension for matching
                        if source_filename.endswith(('.csv', '.xlsx', '.xls')):
                            source_filename_no_ext = source_filename.rsplit('.', 1)[0]
                        else:
                            source_filename_no_ext = source_filename
                
                if "::" in target_col:
                    parts = target_col.split("::")
                    if len(parts) >= 1:
                        target_filename = parts[0]
                        # Remove extension for matching
                        if target_filename.endswith(('.csv', '.xlsx', '.xls')):
                            target_filename_no_ext = target_filename.rsplit('.', 1)[0]
                        else:
                            target_filename_no_ext = target_filename
                
                # Check if both files are in selected files (match by filename)
                source_matches = (source_filename and (source_filename in selected_filenames or source_filename_no_ext in selected_filenames))
                target_matches = (target_filename and (target_filename in selected_filenames or target_filename_no_ext in selected_filenames))
                
                if source_matches and target_matches and source_filename != target_filename:
                    cross_file_rels.append(rel)
        
        if not cross_file_rels:
            return charts
        
        # 1. Relationship Type Distribution
        rel_types = {}
        for rel in cross_file_rels:
            rel_type = rel.get("type", "unknown")
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        if rel_types:
            charts.append({
                "type": "bar",
                "title": "Cross-File Relationship Types",
                "data": {
                    "labels": list(rel_types.keys()),
                    "values": list(rel_types.values())
                },
                "description": "Distribution of relationship types across selected files"
            })
        
        # 2. Relationship Strength Distribution
        strengths = {"strong": 0, "medium": 0, "weak": 0}
        for rel in cross_file_rels:
            strength = rel.get("strength", "medium")
            if strength in strengths:
                strengths[strength] += 1
        
        if sum(strengths.values()) > 0:
            charts.append({
                "type": "pie",
                "title": "Relationship Strength Distribution",
                "data": {
                    "labels": list(strengths.keys()),
                    "values": list(strengths.values())
                },
                "description": "Distribution of relationship strengths"
            })
        
        # 3. Cross-File Connections by File Pair (with readable names)
        file_pairs = {}
        for rel in cross_file_rels:
            source_col = rel.get("source_column", rel.get("column", ""))
            target_col = rel.get("target_column", "")
            
            if source_col and target_col:
                # Extract filenames from column format
                source_filename = None
                target_filename = None
                
                if "::" in source_col:
                    parts = source_col.split("::")
                    if len(parts) >= 1:
                        source_filename = parts[0]
                
                if "::" in target_col:
                    parts = target_col.split("::")
                    if len(parts) >= 1:
                        target_filename = parts[0]
                
                if source_filename and target_filename and source_filename != target_filename:
                    # Use filenames directly (they're already readable)
                    pair_key = f"{source_filename} ↔ {target_filename}"
                    file_pairs[pair_key] = file_pairs.get(pair_key, 0) + 1
        
        if file_pairs:
            charts.append({
                "type": "bar",
                "title": "Cross-File Connections",
                "data": {
                    "labels": list(file_pairs.keys()),
                    "values": list(file_pairs.values())
                },
                "description": "Number of relationships between file pairs"
            })
        
        # 4. Impact Distribution
        impacts = {"critical": 0, "important": 0, "informational": 0}
        for rel in cross_file_rels:
            impact = rel.get("impact", "informational")
            if impact in impacts:
                impacts[impact] += 1
        
        if sum(impacts.values()) > 0:
            charts.append({
                "type": "doughnut",
                "title": "Relationship Impact Distribution",
                "data": {
                    "labels": list(impacts.keys()),
                    "values": list(impacts.values())
                },
                "description": "Distribution of relationship impacts"
            })
        
        return charts
    
    async def generate_cross_file_visualizations(
        self,
        relationships: List[Dict[str, Any]],
        file_ids: List[str],
        file_metadata: Dict[str, Dict[str, Any]],
        filename_to_fileid: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete cross-file visualizations
        
        Args:
            relationships: List of relationship dictionaries
            file_ids: List of selected file IDs
            file_metadata: Dictionary mapping file_id to file metadata
            filename_to_fileid: Dictionary mapping filename to file_id (for matching)
            
        Returns:
            Complete visualization data
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if filename_to_fileid is None:
            filename_to_fileid = {}
        
        # Create a set of filenames for selected files
        selected_filenames = set()
        for file_id in file_ids:
            metadata = file_metadata.get(file_id, {})
            filename = metadata.get("original_filename", "")
            if filename:
                selected_filenames.add(filename)
                # Also add without extension
                filename_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                selected_filenames.add(filename_no_ext)
        
        # Filter relationships to only cross-file ones
        cross_file_relationships = []
        logger.info(f"Filtering {len(relationships)} relationships for {len(file_ids)} selected files")
        logger.info(f"Selected filenames: {selected_filenames}")
        
        for rel in relationships:
            source_col = rel.get("source_column", rel.get("column", ""))
            target_col = rel.get("target_column", "")
            
            # Extract filename from column format: filename::sheet::column
            source_filename = None
            target_filename = None
            
            if source_col and "::" in source_col:
                parts = source_col.split("::")
                if len(parts) >= 1:
                    source_filename = parts[0]
                    # Remove .csv/.xlsx extension if present
                    if source_filename.endswith(('.csv', '.xlsx', '.xls')):
                        source_filename = source_filename.rsplit('.', 1)[0]
            
            if target_col and "::" in target_col:
                parts = target_col.split("::")
                if len(parts) >= 1:
                    target_filename = parts[0]
                    # Remove .csv/.xlsx extension if present
                    if target_filename.endswith(('.csv', '.xlsx', '.xls')):
                        target_filename = target_filename.rsplit('.', 1)[0]
            
            # Also check if relationship has file_id directly
            source_file_id = rel.get("source_file_id", "")
            target_file_id = rel.get("target_file_id", "")
            
            # Try to map filename to file_id if we have the mapping
            if source_filename and source_filename in filename_to_fileid:
                source_file_id = filename_to_fileid[source_filename]
            if target_filename and target_filename in filename_to_fileid:
                target_file_id = filename_to_fileid[target_filename]
            
            # Check if this is a cross-file relationship
            # Method 1: Check by file_id
            if source_file_id and target_file_id:
                if source_file_id in file_ids and target_file_id in file_ids and source_file_id != target_file_id:
                    cross_file_relationships.append(rel)
                    logger.debug(f"Added cross-file relationship (by file_id): {source_file_id} -> {target_file_id}")
                    continue
            
            # Method 2: Check by filename (relationships use filenames)
            if source_filename and target_filename:
                if source_filename in selected_filenames and target_filename in selected_filenames and source_filename != target_filename:
                    cross_file_relationships.append(rel)
                    logger.debug(f"Added cross-file relationship (by filename): {source_filename} -> {target_filename}")
                    continue
        
        logger.info(f"Found {len(cross_file_relationships)} cross-file relationships out of {len(relationships)} total")
        
        # Create relationship graph
        graph = self.create_relationship_graph(cross_file_relationships, file_ids)
        
        # Create charts
        charts = self.create_cross_file_charts(cross_file_relationships, file_ids, file_metadata)
        
        return {
            "file_ids": file_ids,
            "file_count": len(file_ids),
            "relationship_count": len(cross_file_relationships),
            "graph": graph,
            "charts": charts,
            "relationships": cross_file_relationships,
            "summary": {
                "total_relationships": len(cross_file_relationships),
                "node_count": graph["node_count"],
                "edge_count": graph["edge_count"],
                "chart_count": len(charts)
            }
        }

