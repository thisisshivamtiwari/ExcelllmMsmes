"""
Industry Service
Handles industry management and seeding
"""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
import logging

from database import get_database
from models.industry import IndustryCreate, IndustryResponse

logger = logging.getLogger(__name__)


# Pre-defined industries
INDUSTRIES_DATA = [
    {
        "name": "manufacturing",
        "display_name": "Manufacturing",
        "description": "Production, quality control, maintenance, and inventory management data",
        "icon": "🏭",
        "schema_templates": [
            {
                "name": "Production Logs",
                "columns": ["Date", "Product", "Target_Qty", "Actual_Qty", "Line", "Shift"],
                "description": "Daily production tracking with targets and actuals"
            },
            {
                "name": "Quality Control",
                "columns": ["Date", "Product", "Inspected_Qty", "Passed_Qty", "Failed_Qty"],
                "description": "Quality inspection and defect tracking"
            }
        ]
    },
    {
        "name": "retail",
        "display_name": "Retail & E-commerce",
        "description": "Sales, inventory, customer data, and transaction records",
        "icon": "🛒",
        "schema_templates": [
            {
                "name": "Sales Data",
                "columns": ["Date", "Product", "Quantity", "Revenue", "Customer_ID"],
                "description": "Sales transactions and revenue tracking"
            }
        ]
    },
    {
        "name": "healthcare",
        "display_name": "Healthcare",
        "description": "Patient records, appointments, treatments, and medical data",
        "icon": "🏥",
        "schema_templates": [
            {
                "name": "Patient Records",
                "columns": ["Date", "Patient_ID", "Treatment", "Cost", "Status"],
                "description": "Patient treatment and billing records"
            }
        ]
    },
    {
        "name": "finance",
        "display_name": "Finance & Banking",
        "description": "Transactions, accounts, investments, and financial records",
        "icon": "💰",
        "schema_templates": [
            {
                "name": "Transactions",
                "columns": ["Date", "Account_ID", "Amount", "Type", "Category"],
                "description": "Financial transactions and account activity"
            }
        ]
    },
    {
        "name": "education",
        "display_name": "Education",
        "description": "Student records, grades, attendance, and academic data",
        "icon": "🎓",
        "schema_templates": [
            {
                "name": "Student Records",
                "columns": ["Date", "Student_ID", "Subject", "Grade", "Attendance"],
                "description": "Student academic performance tracking"
            }
        ]
    },
    {
        "name": "real_estate",
        "display_name": "Real Estate",
        "description": "Property listings, sales, rentals, and property management data",
        "icon": "🏠",
        "schema_templates": [
            {
                "name": "Property Listings",
                "columns": ["Date", "Property_ID", "Type", "Price", "Status"],
                "description": "Property listings and sales data"
            }
        ]
    },
    {
        "name": "agriculture",
        "display_name": "Agriculture",
        "description": "Crop yields, weather data, livestock, and farm management",
        "icon": "🌾",
        "schema_templates": [
            {
                "name": "Crop Data",
                "columns": ["Date", "Crop_Type", "Yield", "Area", "Weather"],
                "description": "Crop production and yield tracking"
            }
        ]
    },
    {
        "name": "logistics",
        "display_name": "Logistics & Transportation",
        "description": "Shipments, deliveries, routes, and transportation data",
        "icon": "🚚",
        "schema_templates": [
            {
                "name": "Shipments",
                "columns": ["Date", "Shipment_ID", "Origin", "Destination", "Status"],
                "description": "Shipment tracking and logistics data"
            }
        ]
    },
    {
        "name": "hospitality",
        "display_name": "Hospitality & Tourism",
        "description": "Bookings, reservations, guest data, and service records",
        "icon": "🏨",
        "schema_templates": [
            {
                "name": "Bookings",
                "columns": ["Date", "Guest_ID", "Service_Type", "Revenue", "Status"],
                "description": "Hotel and service bookings"
            }
        ]
    },
    {
        "name": "energy",
        "display_name": "Energy & Utilities",
        "description": "Power generation, consumption, billing, and utility data",
        "icon": "⚡",
        "schema_templates": [
            {
                "name": "Energy Consumption",
                "columns": ["Date", "Meter_ID", "Consumption", "Cost", "Type"],
                "description": "Energy consumption and billing data"
            }
        ]
    },
    {
        "name": "technology",
        "display_name": "Technology & IT",
        "description": "Software metrics, system logs, user analytics, and IT data",
        "icon": "💻",
        "schema_templates": [
            {
                "name": "System Metrics",
                "columns": ["Date", "System_ID", "Metric_Type", "Value", "Status"],
                "description": "System performance and monitoring data"
            }
        ]
    },
    {
        "name": "other",
        "display_name": "Other",
        "description": "Custom data for any other industry or use case",
        "icon": "📊",
        "schema_templates": []
    }
]


async def seed_industries():
    """Seed industries collection with pre-defined data"""
    db = get_database()
    industries_collection = db["industries"]
    
    # Check if industries already exist
    count = await industries_collection.count_documents({})
    if count > 0:
        logger.info(f"Industries already seeded ({count} industries)")
        return
    
    # Insert industries
    now = datetime.utcnow()
    industries_to_insert = []
    
    for industry_data in INDUSTRIES_DATA:
        industry_doc = {
            **industry_data,
            "created_at": now
        }
        industries_to_insert.append(industry_doc)
    
    result = await industries_collection.insert_many(industries_to_insert)
    logger.info(f"✅ Seeded {len(result.inserted_ids)} industries")
    
    return result.inserted_ids


async def get_all_industries() -> List[IndustryResponse]:
    """Get all industries"""
    db = get_database()
    industries_collection = db["industries"]
    
    cursor = industries_collection.find({}).sort("display_name", 1)
    industries = []
    
    async for doc in cursor:
        industries.append(IndustryResponse(
            id=str(doc["_id"]),
            name=doc["name"],
            display_name=doc["display_name"],
            description=doc["description"],
            icon=doc.get("icon"),
            schema_templates=doc.get("schema_templates"),
            created_at=doc["created_at"]
        ))
    
    return industries


async def get_industry_by_name(name: str) -> Optional[IndustryResponse]:
    """Get industry by name"""
    db = get_database()
    industries_collection = db["industries"]
    
    doc = await industries_collection.find_one({"name": name})
    if not doc:
        return None
    
    return IndustryResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        display_name=doc["display_name"],
        description=doc["description"],
        icon=doc.get("icon"),
        schema_templates=doc.get("schema_templates"),
        created_at=doc["created_at"]
    )

