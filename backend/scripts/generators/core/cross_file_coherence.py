"""Ensure same facilities, vendors, employees across all datasets."""
from datetime import datetime  # Agar datetime use ho raha hai toh
from .enterprise_state import enterprise
from .travel_personalities import create_employee_persona
from .event_engine import inject_operational_narratives

def initialize_enterprise_state(seed):
    """Call once at start of generation to set up global state."""
    enterprise.__init__(seed)
    rng = enterprise.get_rng()
    
    # Facilities (codes must match those used in SAP, Utility, Travel)
    facilities = [
        ('IN01', 'Pune Manufacturing', 'manufacturing_24x7', 'IN'),
        ('IN02', 'Mumbai Office', 'office', 'IN'),
        ('DE02', 'Frankfurt R&D', 'rd_lab', 'DE'),
        ('US03', 'Chicago Warehouse', 'warehouse', 'US'),
        ('LON02', 'London Sales', 'office', 'GB'),
    ]
    for code, name, ftype, country in facilities:
        enterprise.register_facility(code, {'name': name, 'type': ftype, 'country': country})
    
    # Vendors (consistent IDs across SAP and utility)
    vendors = [
        ('000009981', 'Indian Oil Corp', 'IN', True),
        ('000004611', 'Bharat Petroleum', 'IN', True),
        ('000008821', 'Shell India', 'IN', False),
        ('000000112', 'Total Energies', 'DE', True),
        ('000002211', 'ExxonMobil', 'US', True),
    ]
    for vid, name, country, pref in vendors:
        enterprise.register_vendor(vid, name, country, pref)
    
    # Employees for travel
    for i in range(1, 51):
        eid = f"EMP_{i:03d}"
        persona = create_employee_persona(eid)
        enterprise.register_employee(eid, persona)
    
    # Materials
    materials = [
        ('000000000010002341', 'diesel', 'L', 'SCOPE_1'),
        ('Z_STEEL_456', 'steel', 'MT', 'SCOPE_3'),
        ('LUB-IND-500ML', 'lubricant', 'L', 'SCOPE_1'),
        ('OFF-SUP-001', 'stationery', 'BOX', 'SCOPE_3'),
        ('RMF-HFO-BULK-MT', 'heavy_fuel', 'MT', 'SCOPE_1'),
    ]
    for code, mtype, unit, scope in materials:
        enterprise.register_material(code, mtype, unit, scope)
    
    # Operational narratives
    inject_operational_narratives(datetime(2025,1,1), datetime(2026,5,31))