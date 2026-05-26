"""Employee travel personas – consistent behavior over time."""
from .enterprise_state import enterprise

class TravelPersonality:
    def __init__(self, emp_id, role, freq_multiplier, preferred_cabin, preferred_routes, preferred_airlines, international_ratio):
        self.emp_id = emp_id
        self.role = role
        self.freq_multiplier = freq_multiplier  # 0.2 = rare, 2.0 = frequent
        self.preferred_cabin = preferred_cabin
        self.preferred_routes = preferred_routes  # list of (origin, dest)
        self.preferred_airlines = preferred_airlines
        self.international_ratio = international_ratio  # 0-1
    
    def get_cabin(self):
        return self.preferred_cabin
    
    def get_route(self):
        if self.preferred_routes and enterprise.get_rng().random() < 0.7:
            return enterprise.get_rng().choice(self.preferred_routes)
        # fallback to random valid
        all_routes = [('BOM','DEL'), ('DEL','BOM'), ('BOM','LHR'), ('LHR','JFK'), ('DEL','DXB')]
        return enterprise.get_rng().choice(all_routes)
    
    def should_travel_on_date(self, date):
        # base probability per week
        base = 0.3 * self.freq_multiplier
        # reduce weekends
        if date.weekday() >= 5:
            base *= 0.2
        # increase during audit months (March, September)
        if date.month in [3,9]:
            base *= 1.5
        return enterprise.get_rng().random() < base

# Predefined personas
PERSONAS = {
    'executive': TravelPersonality(None, 'executive', 1.2, 'Business', [('BOM','LHR'), ('DEL','NYC'), ('BOM','SIN')], ['Air India','British Airways','Emirates'], 0.8),
    'regional_sales': TravelPersonality(None, 'sales', 1.8, 'Economy', [('BOM','DEL'), ('DEL','BLR'), ('BLR','BOM')], ['Air India','IndiGo'], 0.05),
    'procurement_manager': TravelPersonality(None, 'procurement', 1.0, 'Economy', [('BOM','Pune'), ('DEL','Mumbai')], ['IndiGo'], 0.0),
    'auditor': TravelPersonality(None, 'audit', 1.5, 'Economy', [('BOM','DEL'), ('DEL','BOM'), ('BOM','LHR')], ['Air India'], 0.2),
    'infrequent': TravelPersonality(None, 'rare', 0.2, 'Economy', [('BOM','DEL')], ['Air India'], 0.0),
}

def create_employee_persona(emp_id):
    role = enterprise.get_rng().choice(list(PERSONAS.keys()))
    p = PERSONAS[role]
    # copy with specific emp_id
    return TravelPersonality(emp_id, p.role, p.freq_multiplier, p.preferred_cabin, p.preferred_routes, p.preferred_airlines, p.international_ratio)