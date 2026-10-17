
import hashlib
import hmac
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import steming



def compare_hashes(local_hash, remote_hash):
    
    return hmac.compare_digest(local_hash, remote_hash )
        
    
def create_hash(text):
    
    text = steming_text(text)
    
    return hashlib.sha256(text.encode()).hexdigest()

def steming_text(text):
    
    return steming.stem_text(text)
    





    
    