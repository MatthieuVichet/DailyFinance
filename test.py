import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:aUMDuGlwLrhVT2YW@db.kezhfytltyrhmgosfwpe.supabase.co:5432/postgres"
engine = create_engine(DB_URL)

categories = [
    {"category": "Salary", "type": "Income", "color": "#FFFFFF", "icon": "💰"},
    {"category": "Gift", "type": "Income", "color": "#FFFFFF", "icon": "🎁"},
    {"category": "Food", "type": "Expense", "color": "#FF0000", "icon": "🍎"},
    {"category": "Party", "type": "Expense", "color": "#FF00FF", "icon": "🎉"},
    {"category": "Hobby", "type": "Expense", "color": "#00FF00", "icon": "🎨"},
    {"category": "Clothes", "type": "Expense", "color": "#0000FF", "icon": "🧥"},
    {"category": "Transport", "type": "Expense", "color": "#FFFF00", "icon": "🚗"},
    {"category": "Home", "type": "Expense", "color": "#FFA500", "icon": "🏠"},
    {"category": "Other", "type": "Expense", "color": "#808080", "icon": "❓"},
    {"category": "Subscription", "type": "Expense", "color": "#3f9056", "icon": "📦"},
]

with engine.begin() as conn:  # transaction
    for cat in categories:
        result = conn.execute(
            text("SELECT COUNT(*) FROM categories WHERE category=:category"),
            {"category": cat["category"]}
        )
        exists = result.scalar() > 0
        if exists:
            conn.execute(
                text("""
                    UPDATE categories
                    SET type=:type, color=:color, icon=:icon
                    WHERE category=:category
                """),
                cat
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO categories (category, type, color, icon)
                    VALUES (:category, :type, :color, :icon)
                """),
                cat
            )

print("Categories migrated successfully!")
