"""Global deterministic enterprise state – single source of truth for all generators."""
import random
import hashlib

class EnterpriseState:
    """Shared state across SAP, Utility, Travel generation."""
    _instance = None
    
    def __new__(cls, seed=42):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, seed=42):
        if self._initialized:
            return
        self.seed = seed
        self.rng = random.Random(seed)
        self._initialized = True
        self._reset_state()
    
    def _reset_state(self):
        self.facilities = {}      # facility_code -> FacilityProfile
        self.vendors = {}         # vendor_id -> {name, country, preferred}
        self.employees = {}       # employee_id -> TravelPersonality
        self.materials = {}       # material_code -> {type, unit, scope}
        self.purchase_orders = [] # list of recurring PO templates
        self.meter_outages = []   # (meter_id, start, end)
        self.correction_chains = [] # (original_id, corrected_id)
        self.narrative_events = [] # list of (date, description)
    
    def register_facility(self, code, profile):
        self.facilities[code] = profile
    
    def register_vendor(self, vid, name, country, is_preferred=False):
        self.vendors[vid] = {'name': name, 'country': country, 'preferred': is_preferred}
    
    def register_employee(self, eid, persona):
        self.employees[eid] = persona
    
    def register_material(self, code, mat_type, unit, scope):
        self.materials[code] = {'type': mat_type, 'unit': unit, 'scope': scope}
    
    def add_narrative(self, date, description):
        self.narrative_events.append((date, description))
    
    def get_rng(self):
        return self.rng

# Global singleton
enterprise = EnterpriseState()