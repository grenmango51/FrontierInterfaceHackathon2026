import sys

def analyze_raw_emotibit(filepath):
    print(f"Reading RAW EmotiBit file: {filepath}")
    
    hr_values = []
    ea_values = []
    
    try:
        with open(filepath, 'r') as f:
            for line_idx, line in enumerate(f):
                parts = line.strip().split(',')
                # EmotiBit data format requires at least 7 columns for metadata
                if len(parts) >= 6:
                    tag = parts[3]
                    if tag == 'HR':
                        # HR payload starts at index 6
                        for val in parts[6:]:
                            try:
                                hr_values.append(float(val))
                            except ValueError:
                                pass
                    elif tag == 'EA':
                        # EA payload starts at index 6
                        for val in parts[6:]:
                            try:
                                ea_values.append(float(val))
                            except ValueError:
                                pass
                                
        print(f"\n--- Data Summary ---")
        print(f"Total lines parsed: {line_idx + 1}")
        print(f"Total HR samples: {len(hr_values)}")
        print(f"Total EA (EDA) samples: {len(ea_values)}")
        
        if len(hr_values) > 0:
            avg_hr = sum(hr_values) / len(hr_values)
            print(f"Average Heart Rate: {avg_hr:.2f} BPM (Min: {min(hr_values):.2f}, Max: {max(hr_values):.2f})")
        
        if len(ea_values) > 0:
            avg_ea = sum(ea_values) / len(ea_values)
            print(f"Average EDA: {avg_ea:.4f} uS (Min: {min(ea_values):.4f}, Max: {max(ea_values):.4f})")
            
    except Exception as e:
        print(f"Error parsing file: {e}")

if __name__ == "__main__":
    analyze_raw_emotibit(r"d:\Frontier Interface\2026-04-24_21-29-04-581986.csv")
