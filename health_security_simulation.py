import time
import sys

# --- Helper for Console Colors (Works in VS Code, Windows Terminal, PowerShell) ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(msg):
    print(f"\n{Colors.HEADER}=== {msg} ==={Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✔ SUCCESS: {msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"{Colors.FAIL}✘ BLOCKED: {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def print_attack(msg):
    print(f"{Colors.WARNING}☠ ATTACK: {msg}{Colors.ENDC}")

# --- The Mock Contract (Digital Twin of your Solidity Code) ---
class HealthAuthRecordsSimulation:
    def __init__(self, admin_addr):
        self.admin = admin_addr
        # Mappings
        self.persons = {admin_addr: {'role': 'None', 'exists': True}} # Admin exists but has no role in enum
        self.access_granted = {} # Nested dict: [patient][doctor] -> bool
        self.records = []
        self.recorded_hashes = set() # Private mapping for replay protection
        
        print_info(f"Contract Deployed. Admin is {self.admin}")

    # Modifiers simulated as check functions
    def _only_admin(self, sender):
        if sender != self.admin:
            raise Exception("only admin")

    def _only_doctor(self, sender):
        p = self.persons.get(sender)
        if not (p and p['exists'] and p['role'] == 'Doctor'):
            raise Exception("only doctor")

    def _only_patient(self, sender):
        p = self.persons.get(sender)
        if not (p and p['exists'] and p['role'] == 'Patient'):
            raise Exception("only patient")

    # Functions
    def register_doctor(self, sender, doctor_addr):
        self._only_admin(sender)
        if not doctor_addr: raise Exception("zero address")
        self.persons[doctor_addr] = {'role': 'Doctor', 'exists': True}
        print_success(f"Doctor registered: {doctor_addr}")

    def register_patient(self, sender, patient_addr):
        self._only_admin(sender)
        if not patient_addr: raise Exception("zero address")
        self.persons[patient_addr] = {'role': 'Patient', 'exists': True}
        print_success(f"Patient registered: {patient_addr}")

    def grant_access(self, sender, doctor_addr):
        self._only_patient(sender)
        # Check doctor validity
        doc = self.persons.get(doctor_addr)
        if not (doc and doc['exists'] and doc['role'] == 'Doctor'):
            raise Exception("invalid doctor")
        
        if sender not in self.access_granted:
            self.access_granted[sender] = {}
        
        self.access_granted[sender][doctor_addr] = True
        print_success(f"Patient {sender} granted access to {doctor_addr}")

    def revoke_access(self, sender, doctor_addr):
        self._only_patient(sender)
        if not self.access_granted.get(sender, {}).get(doctor_addr, False):
            raise Exception("not granted")
        
        self.access_granted[sender][doctor_addr] = False
        print_success(f"Patient {sender} revoked access from {doctor_addr}")

    def add_record(self, sender, patient_addr, record_hash):
        try:
            self._only_doctor(sender)
            
            # Check patient validity
            pat = self.persons.get(patient_addr)
            if not (pat and pat['exists'] and pat['role'] == 'Patient'):
                raise Exception("invalid patient")
            
            # Check Access
            if not self.access_granted.get(patient_addr, {}).get(sender, False):
                raise Exception("access not granted by patient")

            # --- REPLAY HARDENING LOGIC ---
            if record_hash in self.recorded_hashes:
                raise Exception("record hash already exists (data replay blocked)")
            # ------------------------------

            # Add Record
            rec_id = len(self.records)
            new_record = {
                'id': rec_id,
                'patient': patient_addr,
                'doctor': sender,
                'hash': record_hash,
                'time': time.time()
            }
            self.records.append(new_record)
            self.recorded_hashes.add(record_hash)
            
            print_success(f"Record #{rec_id} added by {sender}. Hash: {record_hash[:10]}...")
            
        except Exception as e:
            print_fail(f"Transaction Reverted: {e}")

    def change_admin(self, sender, new_admin):
        try:
            self._only_admin(sender)
            if not new_admin: raise Exception("zero address")
            old = self.admin
            
            # Update old admin
            if old in self.persons:
                self.persons[old]['role'] = 'None'
            
            # Update new admin
            self.admin = new_admin
            self.persons[new_admin] = {'role': 'None', 'exists': True}
            
            print_success(f"Admin changed from {old} to {new_admin}")
        except Exception as e:
            print_fail(f"Transaction Reverted: {e}")

# --- THE STORY ---
def run_simulation():
    print(f"{Colors.BOLD}Starting 'HealthAuthRecords' Smart Contract Simulation...{Colors.ENDC}")
    time.sleep(1)

    # Actors
    ALICE = "0xAlice_Admin"
    BOB = "0xBob_Doctor"
    CHARLIE = "0xCharlie_Patient"
    EVE = "0xEve_The_Hacker"

    # Deploy
    contract = HealthAuthRecordsSimulation(ALICE)

    # --- SCENE 1: The Setup (Happy Path) ---
    print_step("SCENE 1: Setup & Registration")
    contract.register_doctor(ALICE, BOB)
    contract.register_patient(ALICE, CHARLIE)

    # --- SCENE 2: The Consent Flow ---
    print_step("SCENE 2: Access Control")
    # Bob tries to write data BEFORE getting access
    print_info("Dr. Bob tries to write data before Charlie grants access...")
    contract.add_record(BOB, CHARLIE, "Hash_Xray_001")
    
    # Charlie grants access
    print_info("Charlie grants access now...")
    contract.grant_access(CHARLIE, BOB)
    
    # Bob tries again
    print_info("Dr. Bob tries to write data again...")
    contract.add_record(BOB, CHARLIE, "Hash_Xray_001")

    time.sleep(1)

    # --- SCENE 3: The Replay Attack ---
    print_step("SCENE 3: The Replay Attack")
    print_attack("Eve intercepts the transaction for 'Hash_Xray_001'.")
    print_attack("Eve tries to replay (re-submit) the exact same data to confuse the system.")
    
    # Eve pretends to be Bob (or replays Bob's valid signature in a real chain context)
    # Even if Bob submits it again by accident:
    contract.add_record(BOB, CHARLIE, "Hash_Xray_001")
    
    print_info("The contract logic `require(!recordedHashes[recordHash])` prevented duplication.")

    time.sleep(1)

    # --- SCENE 4: The Privilege Escalation Attack ---
    print_step("SCENE 4: Privilege Escalation Attempt")
    print_attack("Eve is tired of games. She attempts to call `changeAdmin` to make herself the boss.")
    
    contract.change_admin(EVE, EVE)
    
    print_info("The `onlyAdmin` modifier successfully blocked Eve.")

    time.sleep(1)

    # --- SCENE 5: The Revocation Test ---
    print_step("SCENE 5: Revoking Access")
    print_info("Charlie is unhappy with Dr. Bob. He revokes access.")
    contract.revoke_access(CHARLIE, BOB)
    
    print_info("Dr. Bob tries to add a new record (Hash_BloodTest_002)...")
    contract.add_record(BOB, CHARLIE, "Hash_BloodTest_002")

    print_step("SIMULATION COMPLETE")

if __name__ == "__main__":
    run_simulation()
