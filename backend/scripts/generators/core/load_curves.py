"""Continuous time-series simulation – no independent hourly randomness."""
import math
from datetime import datetime

class ContinuousLoadCurve:
    def __init__(self, base_load_kw=100, ramp_rate=0.2, noise_std=0.05, equipment_spike_prob=0.01):
        self.base_load = base_load_kw
        self.ramp_rate = ramp_rate   # kW per minute
        self.noise_std = noise_std
        self.equipment_spike_prob = equipment_spike_prob
        self.current_load = base_load_kw
        self.last_hour = None
    
    def generate_hourly(self, start_date, end_date, facility_type='manufacturing'):
        """Generate a continuous sequence of hourly consumption values."""
        hours = []
        current = start_date
        while current <= end_date:
            hour_val = self._get_hour_value(current, facility_type)
            hours.append((current, hour_val))
            current = datetime(current.year, current.month, current.day, current.hour) + timedelta(hours=1)
        return hours
    
    def _get_hour_value(self, dt, facility_type):
        # Deterministic base pattern based on hour of day
        hour = dt.hour
        if facility_type == 'manufacturing_24x7':
            # Overnight baseload
            if hour < 6:
                target = self.base_load * 0.7
            # Morning ramp
            elif 6 <= hour < 9:
                target = self.base_load * (0.7 + (hour-6)/3 * 0.5)
            # Peak day
            elif 9 <= hour < 17:
                target = self.base_load * 1.2
            # Evening decline
            elif 17 <= hour < 22:
                target = self.base_load * (1.2 - (hour-17)/5 * 0.4)
            else:
                target = self.base_load * 0.8
        elif facility_type == 'office':
            if hour < 8 or hour > 18:
                target = self.base_load * 0.1
            elif 8 <= hour < 12:
                target = self.base_load * 0.9
            elif 12 <= hour < 14:
                target = self.base_load * 0.7  # lunch dip
            else:
                target = self.base_load * 1.0
        else:  # warehouse
            if hour < 6:
                target = self.base_load * 0.3
            elif 6 <= hour < 9:
                target = self.base_load * 1.2
            elif 9 <= hour < 17:
                target = self.base_load * 1.0
            else:
                target = self.base_load * 0.6
        
        # Smooth transition from previous hour (inertia)
        if self.last_hour is not None:
            # move 70% toward target
            target = self.last_hour * 0.7 + target * 0.3
        
        # Add realistic noise
        noise = target * self.noise_std * (2 * enterprise.get_rng().random() - 1)
        value = target + noise
        
        # Equipment spikes (e.g., motor start)
        if enterprise.get_rng().random() < self.equipment_spike_prob:
            spike = value * enterprise.get_rng().uniform(1.5, 3.0)
            value = spike
        
        # Weekend / holiday reduction
        if dt.weekday() >= 5:
            value *= 0.4
        # Holiday reduction (simplified)
        if dt.month == 12 and dt.day == 25:
            value *= 0.1
        
        self.last_hour = value
        return max(0, round(value, 2))

# Singleton per facility
load_curves = {}