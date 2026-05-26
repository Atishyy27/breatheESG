"""SAP generation configuration."""
from generators.core.facility_profiles import PLANT_PROFILES

SAP_CONFIG = {
    'target_rows': 1500,
    'delimiter': '|',  # Pipe delimiter like real SAP exports
    'encoding': 'utf-8',
    'fields': [
        'MBLNR', 'MJAHR', 'BLDAT', 'BUDAT', 'WERKS', 'MATNR', 
        'MENGE', 'MEINS', 'ERFMG', 'ERFME', 'BWART', 'SHKZG',
        'NETWR', 'WAERS', 'LIFNR', 'XBLNR'
    ],
    'movement_type_weights': {
        '101': 0.65,  # Goods receipt
        '102': 0.05,  # Reversal
        '122': 0.04,  # Return to vendor
        '201': 0.05,  # Goods issue for cost center
        '261': 0.05,  # Goods issue for order
        '321': 0.03,  # Transfer between batches
        '501': 0.05,  # GR without PO
        '541': 0.08,  # Byproduct receipt
    },
    'anomaly_target': 80,  # Number of rows with anomalies
    'duplicate_doc_count': 15,  # Duplicate material documents
    'plants': list(PLANT_PROFILES.keys()),
}