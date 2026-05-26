"""Temporal distributions for realistic activity patterns."""
from datetime import datetime, timedelta, date
import random
import holidays

# Indian holidays (major ones)
IN_HOLIDAYS = {
    date(2025, 1, 26): "Republic Day",
    date(2025, 8, 15): "Independence Day",
    date(2025, 10, 2): "Gandhi Jayanti",
    date(2025, 12, 25): "Christmas",
    # Diwali (varies, approximate)
    date(2025, 10, 20): "Diwali",
    date(2026, 1, 26): "Republic Day",
    date(2026, 8, 15): "Independence Day",
    date(2026, 12, 25): "Christmas",
}

US_HOLIDAYS = {
    date(2025, 1, 1): "New Year",
    date(2025, 7, 4): "Independence Day",
    date(2025, 12, 25): "Christmas",
    date(2026, 1, 1): "New Year",
    date(2026, 7, 4): "Independence Day",
    date(2026, 12, 25): "Christmas",
}

class TemporalPattern:
    """Generate timestamps with realistic business patterns."""
    
    @staticmethod
    def transaction_probability(dt, plant_type='manufacturing'):
        """Probability (0-2) of a transaction on this datetime."""
        # Base probability
        prob = 1.0
        
        # Weekend reduction
        if dt.weekday() >= 5:
            if plant_type == 'office':
                prob *= 0.1
            elif plant_type == 'manufacturing_24x7':
                prob *= 0.7
            else:
                prob *= 0.3
        
        # Holiday reduction
        date_only = dt.date()
        if date_only in IN_HOLIDAYS or date_only in US_HOLIDAYS:
            prob *= 0.05
        
        # Month-end spike (last 3 days)
        if dt.day >= 28:
            prob *= 1.5
        
        # Fiscal year-end (March) spike for India
        if dt.month == 3 and dt.day >= 25:
            prob *= 2.0
        
        # Summer spike for electricity (May-June)
        if dt.month in [5, 6]:
            prob *= 1.2
        
        return prob
    
    @staticmethod
    def hour_probability(hour, plant_type='manufacturing'):
        """Probability by hour of day."""
        if plant_type == 'office':
            # 9 AM to 5 PM business hours
            if 9 <= hour <= 17:
                return 1.0
            elif hour == 8 or hour == 18:
                return 0.5
            else:
                return 0.1
        elif plant_type == 'manufacturing_24x7':
            # Three shifts, lowest at night
            if 0 <= hour <= 5:
                return 0.6
            elif 6 <= hour <= 22:
                return 1.0
            else:
                return 0.8
        else:
            # Warehouse: morning and evening peaks
            if 8 <= hour <= 12 or 14 <= hour <= 18:
                return 1.0
            else:
                return 0.3
    
    @staticmethod
    def generate_timestamps(start_date, end_date, count, plant_type='manufacturing'):
        """Generate count realistic timestamps with weighted distribution."""
        dates = []
        total_days = (end_date - start_date).days + 1
        
        for _ in range(count * 3):  # oversample then filter
            # Random day with weighted probability
            day_offset = random.randint(0, total_days - 1)
            dt = start_date + timedelta(days=day_offset)
            
            prob_day = TemporalPattern.transaction_probability(dt, plant_type)
            if random.random() > prob_day:
                continue
            
            # Weighted hour
            hour = random.choices(
                range(24),
                weights=[TemporalPattern.hour_probability(h, plant_type) for h in range(24)]
            )[0]
            minute = random.randint(0, 59)
            dt = dt.replace(hour=hour, minute=minute)
            dates.append(dt)
            if len(dates) >= count:
                break
        
        # If not enough, fill with uniform
        while len(dates) < count:
            dt = fake.date_time_between(start_date=start_date, end_date=end_date)
            dates.append(dt)
        
        return sorted(dates)