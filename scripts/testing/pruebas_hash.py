
import hashlib
import hmac
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import steming



def compare_hashes(local_hash, new_hash):
    
    if hmac.compare_digest(local_hash, new_hash):
        
        print('Hashes are the same')
        
    else: 
        print("Hashes are not the same")
    
def create_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def steming_text(text):
    
    return steming.stem_text(text)
    




text1 = 'Hello my name is david díaz and I like play football'
text2 =  'Hello my name is david díaz and I like play football'
text3 = 'This text is different '
text4 = ' Hello my name is david díaz and I like play   football'

text1_stem = steming_text(text1)
text2_stem = steming_text(text2)
text3_stem = steming_text(text3)
text4_stem = steming_text(text4)


hash_1 = create_hash(text1_stem)
hash_2 = create_hash(text2_stem)
hash_3 = create_hash(text3_stem)
hash_4 = create_hash(text4_stem)

#First test: the both text are extactly the same

compare_hashes(hash_1, hash_2)

#Second test: the texts are completly different

compare_hashes(hash_1,hash_3)

#Third test: the texts are almost the same but one of them has a double space

compare_hashes(hash_4, hash_1)

    
    