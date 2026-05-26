#!/usr/bin/env python3
"""Master generator – creates all datasets with specified profile and stateful behavior."""
import sys, os
import argparse
from datetime import datetime, timedelta

from generators.core.export_utils import ExportUtils
from generators.core.corruption_engine import CorruptionEngine
from generators.core.cross_file_coherence import initialize_enterprise_state
from generators.core.enterprise_state import enterprise
from generators.core.event_engine import event_engine
from generators.configs.generation_profiles import PROFILES

# Import generators (they will use the global enterprise state)
from generators.sap.generate_procurement import generate_sap_procurement
from generators.sap.generate_fuel_procurement import generate_fuel_procurement
from generators.utility.generate_monthly_bills import generate_monthly_bills
from generators.utility.generate_interval_data import generate_interval_data
from generators.travel.generate_concur_exports import generate_concur_exports
from generators.travel.generate_itineraries import generate_itineraries


def generate_all(profile_name='realistic', base_output='outputs', seed=42):
    """Generate all datasets with given profile and deterministic seed."""
    print(f"\n{'='*60}")
    print(f"BREATHE ESG DATASET GENERATOR (Stateful)")
    print(f"Profile: {profile_name}")
    print(f"Seed: {seed}")
    print(f"Output: {base_output}/")
    print(f"Start: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # 1. Initialize global deterministic enterprise state
    initialize_enterprise_state(seed)

    profile = PROFILES.get(profile_name, PROFILES['realistic'])

    # Create output subdirectories
    for subdir in ['clean', 'corrupted', 'duplicate_uploads', 'partial_exports', 'stress_test']:
        ExportUtils.ensure_dir(os.path.join(base_output, subdir))

    # 2. Generate CLEAN datasets (zero anomalies, no corruption) - SEED REMOVED FROM CALLS
    print("Generating CLEAN datasets (baseline)...")
    generate_sap_procurement(
        anomaly_count=0, duplicate_count=0, output_path=f"{base_output}/clean/"
    )
    generate_fuel_procurement(
        anomaly_count=0, output_path=f"{base_output}/clean/"
    )
    generate_monthly_bills(
        anomaly_count=0, output_path=f"{base_output}/clean/"
    )
    generate_interval_data(
        anomaly_count=0, output_path=f"{base_output}/clean/"
    )
    generate_concur_exports(
        anomaly_count=0, output_path=f"{base_output}/clean/"
    )
    generate_itineraries(
        anomaly_count=0, output_path=f"{base_output}/clean/"
    )

    # 3. Generate REALISTIC / CORRUPTED datasets based on profile - SEED REMOVED FROM CALLS
    print(f"\nGenerating {profile_name.upper()} datasets (with anomalies & corruption)...")
    generate_sap_procurement(
        anomaly_count=profile['sap_anomalies'],
        duplicate_count=profile['sap_duplicates'],
        output_path=base_output
    )
    generate_fuel_procurement(
        anomaly_count=profile['sap_anomalies'] // 2,
        output_path=base_output
    )
    generate_monthly_bills(
        anomaly_count=profile['utility_anomalies'],
        output_path=base_output
    )
    generate_interval_data(
        anomaly_count=profile['utility_anomalies'] // 2,
        output_path=base_output
    )
    generate_concur_exports(
        anomaly_count=profile['travel_anomalies'],
        output_path=base_output
    )
    generate_itineraries(
        anomaly_count=profile['travel_anomalies'] // 2,
        output_path=base_output
    )

    # 4. Apply file‑level corruption (delimiters, encoding) if profile requests
    if profile.get('corrupt_delimiters') or profile.get('encoding_errors'):
        print("\nApplying file‑level corruption (delimiter chaos, encoding mangle)...")
        for filename in os.listdir(base_output):
            if filename.endswith('.csv'):
                filepath = os.path.join(base_output, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if profile.get('corrupt_delimiters'):
                    content = CorruptionEngine.apply_delimiter_chaos(content)
                if profile.get('encoding_errors'):
                    content = CorruptionEngine.random_encoding_mangle(content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

    # 5. Stress test: partial exports (first 500 rows)
    print("\nGenerating stress test partial exports (first 500 rows)...")
    for src_file in ['sap_procurement.csv', 'utility_bills.csv', 'travel_expenses.json']:
        src_path = os.path.join(base_output, src_file)
        if os.path.exists(src_path):
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            truncated = CorruptionEngine.truncate_file(content, max_rows=500)
            out_path = os.path.join(base_output, 'stress_test', src_file)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(truncated)
            print(f"  -> {out_path}")

    # 6. Duplicate upload test files (byte‑identical copies)
    print("\nGenerating duplicate upload test files...")
    for src_file in ['sap_procurement.csv', 'utility_bills.csv', 'travel_expenses.json']:
        src_path = os.path.join(base_output, src_file)
        if os.path.exists(src_path):
            with open(src_path, 'rb') as f:
                content = f.read()
            dup_path = os.path.join(base_output, 'duplicate_uploads', f"copy_{src_file}")
            with open(dup_path, 'wb') as f:
                f.write(content)
            print(f"  -> {dup_path}")

    # 7. Print narrative summary
    print("\n" + "="*60)
    print("OPERATIONAL NARRATIVES INJECTED:")
    for date, desc in enterprise.narrative_events:
        print(f"  {date.strftime('%Y-%m-%d')}: {desc}")
    print("="*60)
    print(f"Generation complete at {datetime.now().isoformat()}")
    print(f"All outputs in: {base_output}/")
    print("="*60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate ESG test datasets with stateful behavior')
    parser.add_argument('--profile', choices=['clean', 'realistic', 'stress', 'corrupted'],
                        default='realistic', help='Generation profile')
    parser.add_argument('--output', default='outputs', help='Output directory')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    args = parser.parse_args()

    generate_all(profile_name=args.profile, base_output=args.output, seed=args.seed)