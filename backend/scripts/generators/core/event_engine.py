"""Causal anomaly chains – events trigger corruptions, not random injection."""
from .enterprise_state import enterprise
from datetime import datetime, timedelta

class EventEngine:
    def __init__(self):
        self.events = []  # (date, type, affected_entity, description)
    
    def schedule_event(self, date, event_type, entity, description):
        self.events.append((date, event_type, entity, description))
        enterprise.add_narrative(date, description)
    
    def apply_events_to_generation(self, date, source_type, entity_id):
        """Return any anomaly/corruption that should apply to this generation."""
        for ev_date, ev_type, entity, desc in self.events:
            if ev_date == date and entity == entity_id:
                if ev_type == 'meter_outage':
                    return {'skip_row': True, 'reason': desc}
                elif ev_type == 'erp_migration':
                    return {'encoding_corruption': True, 'reason': desc}
                elif ev_type == 'estimated_reading':
                    return {'read_type': 'ESTIMATED', 'reason': desc}
        return None

event_engine = EventEngine()

def inject_operational_narratives(start_date, end_date):
    """Schedule realistic operational events."""
    rng = enterprise.get_rng()
    # Meter outage at IN01 in July
    outage_date = datetime(2025, 7, 15)
    event_engine.schedule_event(outage_date, 'meter_outage', 'MTR-IND-091', 'Meter replacement – 4 hour gap')
    
    # ERP migration in March 2026 – causes encoding corruption across SAP exports
    migration_date = datetime(2026, 3, 1)
    event_engine.schedule_event(migration_date, 'erp_migration', 'SAP', 'SAP ECC to S/4HANA migration – date format issues')
    
    # Estimated reading for DE02 in December due to holidays
    estimated_date = datetime(2025, 12, 20)
    event_engine.schedule_event(estimated_date, 'estimated_reading', 'MTR-GER-442', 'Holiday season – estimated bill')
    
    # Heatwave week – increase diesel procurement
    heatwave_start = datetime(2025, 5, 25)
    for i in range(7):
        d = heatwave_start + timedelta(days=i)
        event_engine.schedule_event(d, 'demand_spike', 'IN01', 'Heatwave – increased diesel for backup generators')