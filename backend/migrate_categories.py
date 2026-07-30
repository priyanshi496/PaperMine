from app.db.database import SessionLocal
from app.db import models
from app.services.llm_service import call_llm_categorize_items

def run_migration():
    db = SessionLocal()
    # Find all line items that are either Uncategorized or NULL
    items = db.query(models.LineItem).filter(
        (models.LineItem.category == None) | 
        (models.LineItem.category == "Uncategorized") |
        (models.LineItem.category == "")
    ).all()
    
    if not items:
        print("No items to migrate.")
        return
        
    # Keep track of item objects and descriptions
    items_to_process = [item for item in items if item.description and item.description.strip()]
    descriptions = [item.description for item in items_to_process]
    
    print(f"Migrating {len(descriptions)} items...")
    
    # Batch them to avoid context limits
    batch_size = 20
    for i in range(0, len(descriptions), batch_size):
        batch_items = items_to_process[i:i+batch_size]
        batch_desc = descriptions[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(descriptions)-1)//batch_size + 1}")
        
        categories = call_llm_categorize_items(batch_desc)
        
        # update DB
        for j, item in enumerate(batch_items):
            if j < len(categories):
                item.category = categories[j]
        
        db.commit()
    
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
