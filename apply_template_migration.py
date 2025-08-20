#!/usr/bin/env python3
"""
Migration script to apply message template schema to existing leveling database.
This script will:
1. Create the new message template tables
2. Insert default message templates
3. Create the template variables and views
"""

import sqlite3
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_utils import get_database_path

def run_migration():
    """Apply the message template schema migration."""
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Please ensure the leveling system is set up first.")
        return False
    
    print("🚀 Starting message template migration...")
    print(f"📁 Database path: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read the message templates schema
        schema_path = os.path.join(os.path.dirname(__file__), 'database', 'message_templates_schema.sql')
        
        if not os.path.exists(schema_path):
            print(f"❌ Schema file not found: {schema_path}")
            return False
            
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print("📋 Executing schema migration...")
        
        # Execute the schema in parts to handle any issues
        sql_statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(sql_statements, 1):
            try:
                cursor.execute(statement)
                print(f"✅ Executed statement {i}/{len(sql_statements)}")
            except sqlite3.Error as e:
                if "table already exists" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"⚠️  Statement {i}: {e} (skipping)")
                else:
                    print(f"❌ Error in statement {i}: {e}")
                    print(f"Statement: {statement[:100]}...")
                    raise
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%template%'")
        template_tables = cursor.fetchall()
        print(f"✅ Created {len(template_tables)} template-related tables: {[t[0] for t in template_tables]}")
        
        # Check if default templates were inserted
        cursor.execute("SELECT COUNT(*) FROM level_up_message_templates")
        template_count = cursor.fetchone()[0]
        print(f"✅ Inserted {template_count} default message templates")
        
        # Check if template variables were inserted
        cursor.execute("SELECT COUNT(*) FROM template_variables")
        var_count = cursor.fetchone()[0]
        print(f"✅ Inserted {var_count} template variables")
        
        conn.close()
        
        print("🎉 Migration completed successfully!")
        print("\n📝 Next steps:")
        print("1. Restart your Discord bot to load the new message system")
        print("2. Access the dashboard to configure custom ranks and message templates")
        print("3. Test the new level-up message system")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🏗️  Leveling System Template Migration")
    print("=" * 50)
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)