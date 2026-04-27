#!/usr/bin/env python3
"""
Brain CT Perfusion Post-Processing and Results Categorization

IMPORTANT CLINICAL CAUTIONS:
1. This tool is for RESEARCH/EDUCATIONAL purposes - NOT for clinical diagnostics
2. Always validate results with qualified radiologists
3. Thresholds vary by imaging protocol, manufacturer, and patient factors
4. Consider clinical context and timing of imaging
5. Artifact detection is critical - motion artifacts can invalidate results
6. Requires trained personnel for interpretation

Required packages: pip install pydicom numpy scipy scikit-image opencv-python
"""

import sys
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum

try:
    import pydicom
    from scipy import ndimage
    from skimage import measure
except ImportError as e:
    print(f"Error: Required package missing: {e}")
    print("Install with: pip install pydicom numpy scipy scikit-image")
    sys.exit(1)


class PerfusionCategory(Enum):
    """Classification of perfusion status"""
    NORMAL = "Normal"
    HYPOPERFUSED = "Hypoperfused"
    HYPERPERFUSED = "Hyperperfused"
    SEVERELY_HYPOPERFUSED = "Severely Hypoperfused"
    ARTIFACT = "Artifact/Invalid"


@dataclass
class PerfusionThresholds:
    """
    Reference thresholds for CT perfusion categorization
    NOTE: These are GENERAL reference values and vary by:
    - Imaging protocol and manufacturer (GE, Siemens, Philips)
    - Patient factors (age, hemodynamics)
    - Brain region
    - Comparison to contralateral hemisphere (preferred method)
    
    Values in typical units:
    - CBF: mL/100g/min
    - CBV: mL/100g
    - MTT: seconds
    """
    # Cerebral Blood Flow (CBF) thresholds
    cbf_normal_min: float = 40.0
    cbf_normal_max: float = 80.0
    cbf_mildly_reduced: float = 30.0
    cbf_severely_reduced: float = 10.0
    
    # Cerebral Blood Volume (CBV) thresholds
    cbv_normal_min: float = 3.0
    cbv_normal_max: float = 8.0
    cbv_abnormal: float = 2.0
    
    # Mean Transit Time (MTT) thresholds (seconds)
    mtt_normal_max: float = 4.5
    mtt_prolonged: float = 6.0
    
    # Time to Peak (TTP) thresholds (seconds)
    ttp_normal_max: float = 5.0
    ttp_delayed: float = 7.0


@dataclass
class PerfusionMetrics:
    """Container for perfusion measurement results"""
    cbf: float  # Cerebral Blood Flow
    cbv: float  # Cerebral Blood Volume
    mtt: float  # Mean Transit Time
    ttp: float  # Time to Peak
    region: str  # Brain region (e.g., "MCA territory")
    category: PerfusionCategory
    confidence: float  # 0-1 score for result reliability
    notes: List[str]  # Clinical notes and warnings


class CTArtifactDetector:
    """Detect artifacts that invalidate perfusion measurements"""
    
    @staticmethod
    def check_motion_artifact(image: np.ndarray, threshold: float = 0.15) -> Tuple[bool, str]:
        """
        Detect motion artifacts using gradient analysis
        
        Args:
            image: 2D image slice
            threshold: Sensitivity threshold (0-1)
        
        Returns:
            (has_artifact, description)
        """
        if image.size == 0:
            return False, "Empty image"
        
        # Calculate gradients
        gx = np.gradient(image, axis=0)
        gy = np.gradient(image, axis=1)
        gradient_magnitude = np.sqrt(gx**2 + gy**2)
        
        # Calculate variance of gradients
        grad_variance = np.var(gradient_magnitude) / (np.mean(np.abs(image)) + 1e-6)
        
        if grad_variance > threshold:
            return True, f"High gradient variance detected: {grad_variance:.3f}"
        
        return False, "No significant motion artifact"
    
    @staticmethod
    def check_beam_hardening(image: np.ndarray) -> Tuple[bool, str]:
        """
        Detect beam hardening artifacts (dark streaks near dense objects)
        
        Args:
            image: 2D image slice
        
        Returns:
            (has_artifact, description)
        """
        # Look for extreme value patterns
        intensity_range = np.max(image) - np.min(image)
        if np.min(image) < -50:  # Typical artifact signature
            return True, "Possible beam hardening artifact detected"
        
        return False, "No significant beam hardening"
    
    @staticmethod
    def check_image_quality(image: np.ndarray) -> float:
        """
        Calculate overall image quality score (0-1)
        
        Args:
            image: 2D image slice
        
        Returns:
            Quality score (1.0 = excellent)
        """
        # Check noise level
        if image.size < 100:
            return 0.0
        
        # Calculate Laplacian using numpy (edge detection)
        # Simple Laplacian filter
        kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
        
        # Pad image for convolution
        padded = np.pad(image.astype(np.float32), 1, mode='edge')
        laplacian = np.zeros_like(padded)
        
        for i in range(1, padded.shape[0] - 1):
            for j in range(1, padded.shape[1] - 1):
                laplacian[i, j] = np.sum(padded[i-1:i+2, j-1:j+2] * kernel)
        
        sharpness = np.var(laplacian)
        
        # Normalize score (empirical scaling)
        quality = min(1.0, sharpness / 100.0)
        return quality


class BrainCTPerfusionProcessor:
    """Process and categorize brain CT perfusion results"""
    
    def __init__(self, thresholds: PerfusionThresholds = None):
        """
        Initialize processor
        
        Args:
            thresholds: Custom thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or PerfusionThresholds()
        self.artifact_detector = CTArtifactDetector()
        self.metrics_history: List[PerfusionMetrics] = []
    
    def categorize_perfusion(self, metrics: Dict[str, float], region: str) -> PerfusionMetrics:
        """
        Categorize perfusion based on metrics
        
        CRITICAL: Always compare to contralateral hemisphere when possible
        
        Args:
            metrics: Dict with keys: cbf, cbv, mtt, ttp
            region: Brain region identifier
        
        Returns:
            PerfusionMetrics with categorization
        """
        cbf = metrics.get('cbf', 0)
        cbv = metrics.get('cbv', 0)
        mtt = metrics.get('mtt', 0)
        ttp = metrics.get('ttp', 0)
        
        notes = []
        confidence = 1.0
        
        # Validate value ranges
        if not (0 < cbf < 200):
            notes.append("WARNING: CBF value outside expected range")
            confidence -= 0.3
        
        if not (0 < cbv < 15):
            notes.append("WARNING: CBV value outside expected range")
            confidence -= 0.3
        
        # Categorization logic (pattern-based approach)
        if confidence < 0.6:
            category = PerfusionCategory.ARTIFACT
            notes.append("Result marked as unreliable - recommend re-scan")
        elif cbf < self.thresholds.cbf_severely_reduced:
            category = PerfusionCategory.SEVERELY_HYPOPERFUSED
            notes.append("CRITICAL: Severe hypoperfusion - possible acute stroke")
        elif cbf < self.thresholds.cbf_mildly_reduced:
            category = PerfusionCategory.HYPOPERFUSED
            notes.append("Hypoperfusion detected")
        elif cbf > self.thresholds.cbf_normal_max + 20:
            category = PerfusionCategory.HYPERPERFUSED
            notes.append("Hyperperfusion detected - check for hyperemia/reperfusion")
        else:
            category = PerfusionCategory.NORMAL
        
        # Additional checks based on pattern
        if mtt > self.thresholds.mtt_prolonged:
            notes.append("Prolonged MTT - suggests compromised circulation")
            confidence *= 0.95
        
        if ttp > self.thresholds.ttp_delayed:
            notes.append("Delayed TTP - circulation delay detected")
            confidence *= 0.95
        
        # Mismatch detection
        if cbf < self.thresholds.cbf_mildly_reduced and cbv > self.thresholds.cbv_normal_min:
            notes.append("CBF-CBV mismatch: Check for collateral circulation")
        
        confidence = max(0.0, min(1.0, confidence))
        
        return PerfusionMetrics(
            cbf=cbf,
            cbv=cbv,
            mtt=mtt,
            ttp=ttp,
            region=region,
            category=category,
            confidence=confidence,
            notes=notes
        )
    
    def process_roi_metrics(self, roi_mask: np.ndarray, 
                           cbf_map: np.ndarray,
                           cbv_map: np.ndarray,
                           mtt_map: np.ndarray,
                           ttp_map: np.ndarray,
                           region: str) -> PerfusionMetrics:
        """
        Extract and process metrics from ROI
        
        Args:
            roi_mask: Binary mask of region of interest
            cbf_map, cbv_map, mtt_map, ttp_map: Perfusion parameter maps
            region: Region identifier
        
        Returns:
            PerfusionMetrics for the region
        """
        # Check for artifacts
        has_motion, motion_msg = self.artifact_detector.check_motion_artifact(cbf_map)
        has_beam, beam_msg = self.artifact_detector.check_beam_hardening(cbf_map)
        quality_score = self.artifact_detector.check_image_quality(cbf_map)
        
        notes = []
        if has_motion:
            notes.append(f"⚠️  {motion_msg}")
        if has_beam:
            notes.append(f"⚠️  {beam_msg}")
        
        # Extract values from ROI
        roi_pixels = roi_mask > 0
        if not np.any(roi_pixels):
            return PerfusionMetrics(
                cbf=0, cbv=0, mtt=0, ttp=0, region=region,
                category=PerfusionCategory.ARTIFACT,
                confidence=0.0,
                notes=["ERROR: Empty ROI"]
            )
        
        # Calculate mean and standard deviation
        cbf_mean = np.mean(cbf_map[roi_pixels])
        cbf_std = np.std(cbf_map[roi_pixels])
        cbv_mean = np.mean(cbv_map[roi_pixels])
        mtt_mean = np.mean(mtt_map[roi_pixels])
        ttp_mean = np.mean(ttp_map[roi_pixels])
        
        # Quality adjustment
        if quality_score < 0.5:
            notes.append("⚠️  Low image quality - interpret with caution")
        
        metrics = {
            'cbf': cbf_mean,
            'cbv': cbv_mean,
            'mtt': mtt_mean,
            'ttp': ttp_mean
        }
        
        result = self.categorize_perfusion(metrics, region)
        result.confidence *= quality_score  # Adjust for image quality
        result.notes.extend(notes)
        
        self.metrics_history.append(result)
        return result
    
    def generate_report(self, patient_id: str, metrics_list: List[PerfusionMetrics]) -> str:
        """
        Generate comprehensive perfusion analysis report
        
        Args:
            patient_id: Patient identifier
            metrics_list: List of PerfusionMetrics
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("BRAIN CT PERFUSION ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Patient ID: {patient_id}")
        report.append(f"Analysis Date: {__import__('datetime').datetime.now()}")
        report.append("\n⚠️  IMPORTANT DISCLAIMER:")
        report.append("This report is for RESEARCH/EDUCATIONAL purposes only.")
        report.append("All results must be validated by qualified radiologists.")
        report.append("Clinical decisions should NOT be based on automated analysis alone.\n")
        
        report.append("PERFUSION RESULTS BY REGION:")
        report.append("-" * 80)
        
        for metrics in metrics_list:
            report.append(f"\nRegion: {metrics.region}")
            report.append(f"  CBF: {metrics.cbf:.2f} mL/100g/min")
            report.append(f"  CBV: {metrics.cbv:.2f} mL/100g")
            report.append(f"  MTT: {metrics.mtt:.2f} sec")
            report.append(f"  TTP: {metrics.ttp:.2f} sec")
            report.append(f"  Category: {metrics.category.value}")
            report.append(f"  Confidence: {metrics.confidence:.1%}")
            
            if metrics.notes:
                report.append("  Notes:")
                for note in metrics.notes:
                    report.append(f"    • {note}")
        
        report.append("\n" + "=" * 80)
        report.append("RECOMMENDATIONS:")
        report.append("  1. Compare with contralateral hemisphere (CRITICAL)")
        report.append("  2. Review patient clinical history")
        report.append("  3. Correlate with structural imaging (CT/MRI)")
        report.append("  4. Consult with neuroradiologist for interpretation")
        report.append("  5. For acute stroke cases, consider repeat perfusion imaging")
        report.append("=" * 80 + "\n")
        
        return "\n".join(report)


def main():
    """Example usage"""
    print("\nBrain CT Perfusion Post-Processing Tool")
    print("=" * 60)
    print("IMPORTANT: This is a research/educational tool only")
    print("All results must be validated by qualified radiologists\n")
    
    # Initialize processor
    processor = BrainCTPerfusionProcessor()
    
    # Example: Simulate perfusion metrics from different regions
    regions_data = [
        {
            'name': 'Right MCA Territory',
            'metrics': {'cbf': 45.2, 'cbv': 5.1, 'mtt': 4.2, 'ttp': 4.8}
        },
        {
            'name': 'Left MCA Territory',
            'metrics': {'cbf': 52.1, 'cbv': 5.5, 'mtt': 3.9, 'ttp': 4.5}
        },
        {
            'name': 'Right PCA Territory',
            'metrics': {'cbf': 12.3, 'cbv': 2.1, 'mtt': 8.5, 'ttp': 10.2}
        },
    ]
    
    results = []
    for region_data in regions_data:
        result = processor.categorize_perfusion(
            region_data['metrics'],
            region_data['name']
        )
        results.append(result)
    
    # Generate report
    report = processor.generate_report("DEMO001", results)
    print(report)
    
    # Save report
    report_file = Path("/Users/gsharma/Programming/supreme-umbrella/ct_perfusion_report.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_file}\n")


if __name__ == "__main__":
    main()
