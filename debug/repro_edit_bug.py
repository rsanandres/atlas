import os
import boto3
from api.session.store_dynamodb import get_session_store
from botocore.exceptions import ClientError
import uuid

# Set env vars
os.environ["AWS_REGION"] = "us-east-1"
os.environ["DDB_ENDPOINT"] = "http://localhost:8001"

def repro_bug():
    print("Reproduction: Attempting to update session name while including PK in UpdateExpression...")
    store = get_session_store()
    
    # 1. Create a dummy session
    sid = str(uuid.uuid4())
    store.update_summary(sid, {"name": "Original Name"}, user_id="test_user")
    print(f"Created session {sid}")
    
    # 2. Get the summary (simulating router.py behavior)
    summary = store.get_summary(sid)
    # summary includes session_id and sk!
    print(f"Got summary keys: {list(summary.keys())}")
    
    # 3. Modify name
    summary["name"] = "New Name"
    
    # 4. Attempt update (simulating router.py call to store.update_summary)
    try:
        store.update_summary(sid, summary, user_id="test_user")
        print("SUCCESS! (Unexpected if bug exists)")
    except ClientError as e:
        print(f"FAILED as expected! Error: {e}")
    except Exception as e:
        print(f"FAILED with unexpected error: {e}")

if __name__ == "__main__":
    repro_bug()
