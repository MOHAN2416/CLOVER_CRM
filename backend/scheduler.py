import time
import datetime
from db import get_db_connection

def scan_overdue_tasks():
    """Scans the database for uncompleted tasks that have passed their deadline."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Query to find tasks that are open and past due
        query = """
        SELECT t.task_id, t.task_type, a.name as account_name, t.due_date 
        FROM tasks t
        JOIN accounts a ON t.account_id = a.account_id
        WHERE t.is_completed = FALSE AND t.due_date < %s
        """
        cursor.execute(query, (now,))
        overdue_items = cursor.fetchall()
        
        if overdue_items:
            print(f"\n⚠️  [WATCHDOG ALERT] - {now}")
            print(f"Detected {len(overdue_items)} overdue task(s) currently stalling the pipeline:")
            for task in overdue_items:
                print(f" - Task #{task['task_id']} ({task['task_type']}) for {task['account_name']} was due on {task['due_date']}")
        else:
            print(f"⏳ [Watchdog Sync] - {now} - All scheduled operations clear.")
            
    except Exception as e:
        print(f"❌ Watchdog script error: {str(e)}")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

if __name__ == "__main__":
    print("🚀 Clover CRM Background Autonomous Watchdog Initialized...")
    print("Monitoring task lifecycle state mutations every 10 seconds. Press Ctrl+C to terminate.")
    
    # Run an infinite execution loop to simulate a background daemon process
    while True:
        scan_overdue_tasks()
        time.sleep(10) # Checks the database every 10 seconds