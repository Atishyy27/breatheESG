"""Inject deliberate data quality issues."""
import random
import copy
from datetime import datetime, timedelta

class AnomalyInjector:
    """Inject validation errors and edge cases."""
    
    ANOMALY_TYPES = [
        'missing_quantity',
        'negative_value',
        'future_date',
        'impossible_unit',
        'duplicate_row',
        'encoding_corruption',
        'excel_date_mangle',
        'missing_required_column',
        'trailing_whitespace',
        'empty_string_field',
        'out_of_range_value',
        'inconsistent_currency',
    ]
    
    @staticmethod
    def inject_anomalies(rows, target_count=50):
        """Inject exactly target_count anomalies across rows."""
        if not rows or target_count == 0:
            return rows
        
        rows_copy = [dict(r) for r in rows]  # deep-ish copy
        indices = random.sample(range(len(rows_copy)), min(target_count, len(rows_copy)))
        
        for idx in indices:
            anomaly = random.choice(AnomalyInjector.ANOMALY_TYPES)
            AnomalyInjector._apply_anomaly(rows_copy[idx], anomaly)
        
        return rows_copy
    
    @staticmethod
    def _apply_anomaly(row, anomaly_type):
        """Apply specific anomaly to a row."""
        if anomaly_type == 'missing_quantity':
            if 'MENGE' in row:
                row['MENGE'] = ''
            elif 'consumption_kwh' in row:
                row['consumption_kwh'] = ''
        
        elif anomaly_type == 'negative_value':
            if 'MENGE' in row and row.get('MENGE'):
                try:
                    row['MENGE'] = -abs(float(row['MENGE']))
                except:
                    pass
            elif 'consumption_kwh' in row and row.get('consumption_kwh'):
                try:
                    row['consumption_kwh'] = -abs(float(row['consumption_kwh']))
                except:
                    pass
        
        elif anomaly_type == 'future_date':
            future = (datetime.now() + timedelta(days=365)).strftime('%d%m%Y')
            for key in ['BUDAT', 'BLDAT', 'transaction_date', 'billing_end']:
                if key in row:
                    row[key] = future
                    break
        
        elif anomaly_type == 'impossible_unit':
            if 'MEINS' in row:
                row['MEINS'] = random.choice(['ZZZ', 'INVALID', ''])
            elif 'unit' in row:
                row['unit'] = 'IMPOSSIBLE'
        
        elif anomaly_type == 'duplicate_row':
            # Mark for duplication later (handled in generator)
            row['__duplicate'] = True
        
        elif anomaly_type == 'encoding_corruption':
            # Simulate UTF-8 misinterpretation
            for key in ['MATNR', 'WERKS', 'vendor']:
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].replace('e', 'Ã©').replace('i', 'Ã¯')
                    break
        
        elif anomaly_type == 'excel_date_mangle':
            for key in ['BUDAT', 'BLDAT', 'billing_start']:
                if key in row and isinstance(row[key], str):
                    # Convert DDMMYYYY to MM/DD/YYYY
                    if len(row[key]) == 8 and row[key].isdigit():
                        row[key] = f"{row[key][4:6]}/{row[key][6:8]}/{row[key][0:4]}"
                    break
        
        elif anomaly_type == 'missing_required_column':
            # Remove a column that should exist (handled in generator)
            row['__missing_column'] = True
        
        elif anomaly_type == 'trailing_whitespace':
            for key in ['WERKS', 'MATNR', 'origin', 'destination']:
                if key in row and isinstance(row[key], str):
                    row[key] = row[key] + '   '
                    break
        
        elif anomaly_type == 'empty_string_field':
            for key in ['MATNR', 'LIFNR', 'vendor']:
                if key in row:
                    row[key] = ''
                    break
        
        elif anomaly_type == 'out_of_range_value':
            if 'MENGE' in row and row.get('MENGE'):
                try:
                    row['MENGE'] = float(row['MENGE']) * 1000
                except:
                    pass
        
        elif anomaly_type == 'inconsistent_currency':
            if 'WAERS' in row:
                row['WAERS'] = random.choice(['XYZ', 'ABC', ''])
    
    @staticmethod
    def inject_duplicates(rows, duplicate_count=10):
        """Insert duplicate rows."""
        if not rows:
            return rows
        duplicates = []
        for _ in range(duplicate_count):
            original = random.choice(rows)
            dup = copy.deepcopy(original)
            if 'MBLNR' in dup:
                # Keep same doc number but add a flag
                dup['__is_duplicate'] = True
            duplicates.append(dup)
        return rows + duplicates