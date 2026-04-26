#!/usr/bin/env python3
"""
Script to check and display primary DICOM tags from a DICOM file.
Requires: pip install pydicom
"""

import sys
from pathlib import Path
try:
    import pydicom
except ImportError:
    print("Error: pydicom is not installed. Install it with: pip install pydicom")
    sys.exit(1)


def check_dicom_tags(dicom_file):
    """
    Read a DICOM file and display all primary tags.
    
    Args:
        dicom_file (str): Path to the DICOM file
    """
    try:
        # Load DICOM file
        dcm = pydicom.dcmread(dicom_file)
        print(f"\n{'='*70}")
        print(f"DICOM File: {dicom_file}")
        print(f"{'='*70}\n")
        
        # Define primary tags with their meanings
        primary_tags = {
            "Patient Information": [
                ((0x0010, 0x0010), "Patient Name"),
                ((0x0010, 0x0020), "Patient ID"),
                ((0x0010, 0x0030), "Patient Birth Date"),
                ((0x0010, 0x0040), "Patient Sex"),
            ],
            "Study Information": [
                ((0x0020, 0x000D), "Study Instance UID"),
                ((0x0008, 0x0020), "Study Date"),
                ((0x0008, 0x0030), "Study Time"),
                ((0x0008, 0x1030), "Study Description"),
                ((0x0008, 0x0050), "Accession Number"),
            ],
            "Series Information": [
                ((0x0020, 0x000E), "Series Instance UID"),
                ((0x0008, 0x0020), "Series Date"),
                ((0x0008, 0x0030), "Series Time"),
                ((0x0008, 0x103E), "Series Description"),
                ((0x0020, 0x0011), "Series Number"),
            ],
            "Image/SOP Instance Information": [
                ((0x0008, 0x0016), "SOP Class UID"),
                ((0x0008, 0x0018), "SOP Instance UID"),
                ((0x0020, 0x0013), "Instance Number"),
                ((0x0008, 0x0008), "Image Type"),
                ((0x0008, 0x0060), "Modality"),
            ],
            "Image Pixel Data and Attributes": [
                ((0x0028, 0x0010), "Rows"),
                ((0x0028, 0x0011), "Columns"),
                ((0x0028, 0x0100), "Bits Allocated"),
                ((0x0028, 0x0101), "Bits Stored"),
                ((0x0028, 0x0102), "High Bit"),
                ((0x0028, 0x0103), "Pixel Representation"),
                ((0x0028, 0x0002), "Samples per Pixel"),
                ((0x0028, 0x0004), "Photometric Interpretation"),
                ((0x7FE0, 0x0010), "Pixel Data (size)"),
            ],
        }
        
        # Display tags by category
        for category, tags in primary_tags.items():
            print(f"\n{category}:")
            print("-" * 70)
            
            for tag, description in tags:
                try:
                    if tag in dcm:
                        value = dcm[tag].value
                        
                        # Special handling for Pixel Data (just show size)
                        if tag == (0x7FE0, 0x0010):
                            if hasattr(value, '__len__'):
                                print(f"  ✓ {description:40} {len(value):>15} bytes")
                            else:
                                print(f"  ✓ {description:40} {'[Present]':>15}")
                        else:
                            # Truncate long values
                            value_str = str(value)
                            if len(value_str) > 45:
                                value_str = value_str[:42] + "..."
                            print(f"  ✓ {description:40} {value_str:>15}")
                    else:
                        print(f"  ✗ {description:40} {'[Not Present]':>15}")
                except Exception as e:
                    print(f"  ? {description:40} {'[Error]':>15}")
        
        print(f"\n{'='*70}")
        print(f"Total tags in file: {len(dcm)}")
        print(f"{'='*70}\n")
        
    except pydicom.errors.InvalidDicomError:
        print(f"Error: '{dicom_file}' is not a valid DICOM file.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{dicom_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading DICOM file: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python check_dicom_tags.py <path_to_dicom_file>")
        print("\nExample: python check_dicom_tags.py image.dcm")
        print("\nThis script checks and displays all primary DICOM tags.")
        sys.exit(1)
    
    dicom_file = sys.argv[1]
    check_dicom_tags(dicom_file)


if __name__ == "__main__":
    main()
