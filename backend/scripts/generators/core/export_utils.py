"""Utilities for exporting datasets to various formats."""
import json
import csv
import os
from datetime import datetime

class ExportUtils:
    """Handle file exports with proper formatting."""
    
    @staticmethod
    def export_csv(filename, rows, fieldnames=None, delimiter=','):
        """Export rows to CSV with given delimiter."""
        if not rows:
            return
        if not fieldnames:
            fieldnames = list(rows[0].keys())
            # Remove internal keys
            fieldnames = [f for f in fieldnames if not f.startswith('__')]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            for row in rows:
                clean_row = {k: v for k, v in row.items() if not k.startswith('__')}
                writer.writerow(clean_row)
        print(f"Exported {len(rows)} rows to {filename}")
    
    @staticmethod
    def export_json(filename, rows, indent=2):
        """Export rows to JSON."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=indent, default=str)
        print(f"Exported {len(rows)} records to {filename}")
    
    @staticmethod
    def ensure_dir(path):
        """Create directory if not exists."""
        os.makedirs(path, exist_ok=True)