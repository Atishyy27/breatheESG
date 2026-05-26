"""Master generation profiles for different testing scenarios."""
from .sap_config import SAP_CONFIG
from .utility_config import UTILITY_CONFIG
from .travel_config import TRAVEL_CONFIG

PROFILES = {
    'clean': {
        'sap_anomalies': 0,
        'utility_anomalies': 0,
        'travel_anomalies': 0,
        'sap_duplicates': 0,
        'corrupt_delimiters': False,
        'encoding_errors': False,
    },
    'realistic': {
        'sap_anomalies': SAP_CONFIG['anomaly_target'],
        'utility_anomalies': UTILITY_CONFIG['anomaly_target'],
        'travel_anomalies': TRAVEL_CONFIG['anomaly_target'],
        'sap_duplicates': SAP_CONFIG['duplicate_doc_count'],
        'corrupt_delimiters': True,
        'encoding_errors': False,
    },
    'stress': {
        'sap_anomalies': SAP_CONFIG['anomaly_target'] * 2,
        'utility_anomalies': UTILITY_CONFIG['anomaly_target'] * 2,
        'travel_anomalies': TRAVEL_CONFIG['anomaly_target'] * 2,
        'sap_duplicates': SAP_CONFIG['duplicate_doc_count'] * 2,
        'corrupt_delimiters': True,
        'encoding_errors': True,
    },
    'corrupted': {
        'sap_anomalies': SAP_CONFIG['anomaly_target'],
        'utility_anomalies': UTILITY_CONFIG['anomaly_target'],
        'travel_anomalies': TRAVEL_CONFIG['anomaly_target'],
        'sap_duplicates': SAP_CONFIG['duplicate_doc_count'],
        'corrupt_delimiters': True,
        'encoding_errors': True,
    },
}