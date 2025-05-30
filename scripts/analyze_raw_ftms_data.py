#!/usr/bin/env python3
"""
Raw FTMS Data Analyzer

This script analyzes raw FTMS data collected by collect_raw_ftms_data.py
and helps debug the FTMS parser by showing detailed packet structure.

Usage:
    python analyze_raw_ftms_data.py [--input FILE] [--verbose]
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

def parse_flags(byte0: int, byte1: int) -> Dict[str, bool]:
    """Parse FTMS flags from the first two bytes."""
    return {
        # Byte 0 flags
        "more_data_speed": bool(byte0 & 0b00000001),
        "average_speed": bool(byte0 & 0b00000010),
        "instantaneous_cadence": bool(byte0 & 0b00000100),
        "average_cadence": bool(byte0 & 0b00001000),
        "total_distance": bool(byte0 & 0b00010000),
        "resistance_level": bool(byte0 & 0b00100000),
        "instantaneous_power": bool(byte0 & 0b01000000),
        "average_power": bool(byte0 & 0b10000000),
        
        # Byte 1 flags
        "expended_energy": bool(byte1 & 0b00000001),
        "heart_rate": bool(byte1 & 0b00000010),
        "metabolic_equivalent": bool(byte1 & 0b00000100),
        "elapsed_time": bool(byte1 & 0b00001000),
        "remaining_time": bool(byte1 & 0b00010000),
    }

def analyze_packet_structure(raw_bytes: List[int]) -> Dict[str, Any]:
    """Analyze the structure of an FTMS packet."""
    if len(raw_bytes) < 2:
        return {"error": "Packet too short"}
    
    flags = parse_flags(raw_bytes[0], raw_bytes[1])
    analysis = {
        "length": len(raw_bytes),
        "flags_byte0": f"0x{raw_bytes[0]:02x}",
        "flags_byte1": f"0x{raw_bytes[1]:02x}",
        "flags": flags,
        "data_fields": [],
        "expected_length": 2  # Start with flags
    }
    
    # Analyze expected data fields based on flags
    offset = 2
    
    if flags["more_data_speed"]:
        analysis["data_fields"].append({
            "field": "instant_speed",
            "offset": offset,
            "length": 2,
            "unit": "km/h * 100"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value / 100.0
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["average_speed"]:
        analysis["data_fields"].append({
            "field": "average_speed",
            "offset": offset,
            "length": 2,
            "unit": "km/h * 100"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value / 100.0
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["instantaneous_cadence"]:
        analysis["data_fields"].append({
            "field": "instant_cadence",
            "offset": offset,
            "length": 2,
            "unit": "rpm * 2"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value / 2.0
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["average_cadence"]:
        analysis["data_fields"].append({
            "field": "average_cadence",
            "offset": offset,
            "length": 2,
            "unit": "rpm * 2"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value / 2.0
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["total_distance"]:
        analysis["data_fields"].append({
            "field": "total_distance",
            "offset": offset,
            "length": 3,
            "unit": "meters"
        })
        if offset + 3 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+3], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 3
        analysis["expected_length"] += 3
    
    if flags["resistance_level"]:
        analysis["data_fields"].append({
            "field": "resistance_level",
            "offset": offset,
            "length": 2,
            "unit": "unitless"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=True)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["instantaneous_power"]:
        analysis["data_fields"].append({
            "field": "instant_power",
            "offset": offset,
            "length": 2,
            "unit": "watts"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=True)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["average_power"]:
        analysis["data_fields"].append({
            "field": "average_power",
            "offset": offset,
            "length": 2,
            "unit": "watts"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=True)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["expended_energy"]:
        analysis["data_fields"].append({
            "field": "expended_energy",
            "offset": offset,
            "length": 5,
            "unit": "total(2) + per_hour(2) + per_minute(1)"
        })
        if offset + 5 <= len(raw_bytes):
            total = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            per_hour = int.from_bytes(raw_bytes[offset+2:offset+4], "little", signed=False)
            per_minute = int.from_bytes(raw_bytes[offset+4:offset+5], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = {
                "total": total,
                "per_hour": per_hour,
                "per_minute": per_minute
            }
            analysis["data_fields"][-1]["converted_value"] = {
                "total_kcal": total,
                "kcal_per_hour": per_hour,
                "kcal_per_minute": per_minute
            }
        offset += 5
        analysis["expected_length"] += 5
    
    if flags["heart_rate"]:
        analysis["data_fields"].append({
            "field": "heart_rate",
            "offset": offset,
            "length": 1,
            "unit": "bpm"
        })
        if offset + 1 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+1], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 1
        analysis["expected_length"] += 1
    
    if flags["metabolic_equivalent"]:
        analysis["data_fields"].append({
            "field": "metabolic_equivalent",
            "offset": offset,
            "length": 1,
            "unit": "METs * 10"
        })
        if offset + 1 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+1], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value / 10.0
        offset += 1
        analysis["expected_length"] += 1
    
    if flags["elapsed_time"]:
        analysis["data_fields"].append({
            "field": "elapsed_time",
            "offset": offset,
            "length": 2,
            "unit": "seconds"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 2
        analysis["expected_length"] += 2
    
    if flags["remaining_time"]:
        analysis["data_fields"].append({
            "field": "remaining_time",
            "offset": offset,
            "length": 2,
            "unit": "seconds"
        })
        if offset + 2 <= len(raw_bytes):
            value = int.from_bytes(raw_bytes[offset:offset+2], "little", signed=False)
            analysis["data_fields"][-1]["raw_value"] = value
            analysis["data_fields"][-1]["converted_value"] = value
        offset += 2
        analysis["expected_length"] += 2
    
    # Check for unexpected data
    if len(raw_bytes) > analysis["expected_length"]:
        analysis["unexpected_data"] = {
            "offset": analysis["expected_length"],
            "length": len(raw_bytes) - analysis["expected_length"],
            "bytes": raw_bytes[analysis["expected_length"]:]
        }
    
    return analysis

def analyze_data_file(file_path: Path, verbose: bool = False):
    """Analyze a raw FTMS data file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    if "collection_info" not in data or "packets" not in data:
        print("❌ Invalid data file format")
        return
    
    info = data["collection_info"]
    packets = data["packets"]
    
    print("📊 FTMS Data Analysis Report")
    print("=" * 50)
    
    # Collection info
    print(f"\n🔍 Collection Info:")
    print(f"   • Device: {info.get('device_name', 'Unknown')} ({info.get('device_address', 'Unknown')})")
    print(f"   • Start time: {info.get('start_time_iso', 'Unknown')}")
    print(f"   • Duration: {info.get('duration_seconds', 0):.1f} seconds")
    print(f"   • Total packets: {info.get('packet_count', 0)}")
    
    if not packets:
        print("⚠️  No packets to analyze")
        return
    
    # Packet length analysis
    lengths = [p['packet_length'] for p in packets]
    length_counts = Counter(lengths)
    
    print(f"\n📏 Packet Length Distribution:")
    for length, count in sorted(length_counts.items()):
        print(f"   • {length} bytes: {count} packets ({count/len(packets)*100:.1f}%)")
    
    # Flag analysis
    print(f"\n🏁 Flag Analysis:")
    flag_counts = {}
    
    for packet in packets:
        raw_bytes = packet['raw_bytes']
        if len(raw_bytes) >= 2:
            flags = parse_flags(raw_bytes[0], raw_bytes[1])
            for flag_name, flag_value in flags.items():
                if flag_name not in flag_counts:
                    flag_counts[flag_name] = {"true": 0, "false": 0}
                flag_counts[flag_name]["true" if flag_value else "false"] += 1
    
    for flag_name, counts in sorted(flag_counts.items()):
        total = counts["true"] + counts["false"]
        true_pct = counts["true"] / total * 100 if total > 0 else 0
        print(f"   • {flag_name}: {counts['true']}/{total} packets ({true_pct:.1f}%)")
    
    # Sample packet analysis
    print(f"\n📋 Sample Packet Analysis:")
    
    # Analyze first few unique packet structures
    seen_structures = set()
    sample_count = 0
    max_samples = 5 if not verbose else 10
    
    for i, packet in enumerate(packets):
        raw_bytes = packet['raw_bytes']
        
        # Create a signature for this packet structure
        if len(raw_bytes) >= 2:
            structure_sig = (raw_bytes[0], raw_bytes[1], len(raw_bytes))
            
            if structure_sig not in seen_structures and sample_count < max_samples:
                seen_structures.add(structure_sig)
                sample_count += 1
                
                print(f"\n   Sample packet #{i+1}:")
                print(f"   Raw bytes: {' '.join([f'{b:02x}' for b in raw_bytes])}")
                
                analysis = analyze_packet_structure(raw_bytes)
                print(f"   Length: {analysis['length']} bytes (expected: {analysis['expected_length']})")
                print(f"   Flags: {analysis['flags_byte0']} {analysis['flags_byte1']}")
                
                active_flags = [name for name, value in analysis['flags'].items() if value]
                if active_flags:
                    print(f"   Active flags: {', '.join(active_flags)}")
                
                if analysis['data_fields']:
                    print(f"   Data fields:")
                    for field in analysis['data_fields']:
                        if 'converted_value' in field:
                            print(f"     • {field['field']}: {field['converted_value']} {field['unit']}")
                        else:
                            print(f"     • {field['field']}: <missing data> {field['unit']}")
                
                if 'unexpected_data' in analysis:
                    unexpected = analysis['unexpected_data']
                    print(f"   ⚠️  Unexpected data at offset {unexpected['offset']}: {' '.join([f'{b:02x}' for b in unexpected['bytes']])}")
    
    if verbose:
        # Detailed packet-by-packet analysis
        print(f"\n📝 Detailed Packet Log:")
        for i, packet in enumerate(packets[:20]):  # Show first 20 packets
            timestamp = packet.get('timestamp', 0)
            elapsed = timestamp - packets[0].get('timestamp', 0) if packets else 0
            raw_bytes = packet['raw_bytes']
            
            analysis = analyze_packet_structure(raw_bytes)
            
            print(f"\n   Packet #{i+1} (t={elapsed:.1f}s):")
            print(f"   {packet['hex_string']}")
            
            # Show parsed values
            values = []
            for field in analysis['data_fields']:
                if 'converted_value' in field:
                    values.append(f"{field['field']}={field['converted_value']}")
            
            if values:
                print(f"   Parsed: {', '.join(values)}")
        
        if len(packets) > 20:
            print(f"\n   ... ({len(packets) - 20} more packets)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze raw FTMS data")
    parser.add_argument("--input", "-i", default="raw_ftms_data.json", help="Input data file (default: raw_ftms_data.json)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed packet-by-packet analysis")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print("💡 Run collect_raw_ftms_data.py first to collect data")
        return
    
    analyze_data_file(input_path, args.verbose)

if __name__ == "__main__":
    main() 