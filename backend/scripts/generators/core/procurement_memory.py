"""Stateful procurement behavior – repeated vendors, materials, POs."""
from .enterprise_state import enterprise
from .facility_profiles import get_plant_profile

class ProcurementMemory:
    def __init__(self):
        self.po_counter = 5000000000
        self.material_inventory = {}  # facility -> {material_code: last_order_date, total_qty}
        self.vendor_contracts = {}    # facility -> {vendor_id: [material_codes]}
    
    def get_next_po_number(self):
        self.po_counter += 1
        return str(self.po_counter)
    
    def get_recurring_materials(self, facility_code):
        """Return list of (material_code, weight, unit, scope) for this facility."""
        profile = get_plant_profile(facility_code)
        materials = profile.get('materials', {})
        result = []
        for mat_name, config in materials.items():
            # Map friendly name to realistic material code
            if mat_name == 'diesel':
                code = '000000000010002341'
            elif mat_name == 'steel':
                code = 'Z_STEEL_456'
            elif mat_name == 'lubricants':
                code = 'LUB-IND-500ML'
            elif mat_name == 'office_supplies':
                code = 'OFF-SUP-001'
            else:
                code = f"MAT-{mat_name[:3].upper()}-{facility_code}"
            result.append((code, config['weight'], config['unit'], config['scope']))
        return result
    
    def get_preferred_vendor(self, facility_code, material_code):
        """Return vendor ID based on facility profile and material."""
        profile = get_plant_profile(facility_code)
        vendors = profile.get('primary_vendors', ['000009981'])
        # deterministic choice based on material hash
        rng = enterprise.get_rng()
        # but make it consistent: vendor depends on material
        idx = hash(material_code) % len(vendors)
        return vendors[idx]
    
    def record_order(self, facility_code, material_code, vendor, quantity, date):
        """Update inventory for future spikes / seasonality."""
        key = (facility_code, material_code)
        if key not in self.material_inventory:
            self.material_inventory[key] = {'last_date': date, 'total_qty': 0, 'orders': []}
        self.material_inventory[key]['last_date'] = date
        self.material_inventory[key]['total_qty'] += quantity
        self.material_inventory[key]['orders'].append((date, quantity))
    
    def get_seasonal_multiplier(self, date, facility_code, material_code):
        """Fiscal quarter spikes, summer diesel etc."""
        # March spike for India facilities
        if facility_code.startswith('IN') and date.month == 3 and date.day >= 25:
            return 2.0
        # Summer diesel increase for cooling
        if material_code.endswith('DIESEL') and date.month in [5,6]:
            return 1.3
        return 1.0

procurement_memory = ProcurementMemory()