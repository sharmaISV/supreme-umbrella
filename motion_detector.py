#!/usr/bin/env python3
"""
Automatic Motion Detection in CT Perfusion Data

This module detects and quantifies motion artifacts in brain CT perfusion studies.
Multiple detection methods to identify various types of motion:
- Translation (patient shift)
- Rotation (head tilt/rotation)
- Pulsatile motion (cardiac/respiratory)
- High-frequency noise indicating motion

IMPORTANT: Motion detection flags need radiologist validation for clinical use
"""

import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import pydicom
    from scipy import ndimage, signal, fft
    from scipy.ndimage import binary_erosion, binary_dilation
except ImportError as e:
    print(f"Error: Required package missing: {e}")
    print("Install with: pip install pydicom numpy scipy")
    sys.exit(1)


class MotionSeverity(Enum):
    """Classification of motion severity"""
    NONE = "No Motion Detected"
    MINIMAL = "Minimal Motion"
    MILD = "Mild Motion"
    MODERATE = "Moderate Motion"
    SEVERE = "Severe Motion"


@dataclass
class MotionMetrics:
    """Container for motion detection results"""
    severity: MotionSeverity
    translation_score: float  # 0-100
    rotation_score: float  # 0-100
    pulsatile_score: float  # 0-100
    noise_score: float  # 0-100
    overall_score: float  # 0-100 (weighted average)
    affected_slices: List[int]
    affected_frames: List[int]
    motion_description: str
    recommendations: List[str]
    confidence: float  # 0-1


class MotionDetector:
    """
    Comprehensive motion detection for CT perfusion data
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize motion detector
        
        Args:
            verbose: Print detailed analysis information
        """
        self.verbose = verbose
        self.analysis_log = []
    
    def _log(self, message: str):
        """Log analysis messages"""
        if self.verbose:
            print(f"[Motion Analysis] {message}")
        self.analysis_log.append(message)
    
    def detect_translation_motion(self, image_series: np.ndarray) -> Tuple[float, List[int]]:
        """
        Detect patient translation (XY shift) using centroid tracking
        
        Args:
            image_series: 3D array (frames, height, width)
        
        Returns:
            (translation_score, affected_frame_indices)
        """
        self._log("Analyzing translation motion...")
        
        if image_series.ndim != 3:
            return 0.0, []
        
        frames, height, width = image_series.shape
        centroids = []
        
        # Calculate centroid for each frame
        for i in range(frames):
            frame = image_series[i]
            # Normalize and threshold
            normalized = (frame - np.min(frame)) / (np.max(frame) - np.min(frame) + 1e-6)
            binary = normalized > 0.5
            
            if np.sum(binary) > 0:
                y_coords, x_coords = np.where(binary)
                centroid_y = np.mean(y_coords)
                centroid_x = np.mean(x_coords)
                centroids.append((centroid_x, centroid_y))
        
        if len(centroids) < 2:
            return 0.0, []
        
        # Calculate frame-to-frame displacement
        displacements = []
        for i in range(1, len(centroids)):
            dx = centroids[i][0] - centroids[i-1][0]
            dy = centroids[i][1] - centroids[i-1][1]
            distance = np.sqrt(dx**2 + dy**2)
            displacements.append(distance)
        
        displacements = np.array(displacements)
        
        # Detect large jumps (>2 pixels = suspicious)
        threshold_pixels = 2.0
        affected_frames = [i+1 for i, d in enumerate(displacements) if d > threshold_pixels]
        
        # Score: 0-100 based on maximum displacement
        max_displacement = np.max(displacements) if len(displacements) > 0 else 0
        translation_score = min(100, (max_displacement / 5.0) * 100)  # Normalize
        
        self._log(f"  Max translation: {max_displacement:.2f} pixels")
        self._log(f"  Affected frames: {len(affected_frames)}/{frames}")
        self._log(f"  Translation score: {translation_score:.1f}")
        
        return translation_score, affected_frames
    
    def detect_rotation_motion(self, image_series: np.ndarray) -> Tuple[float, List[int]]:
        """
        Detect rotational motion using image correlation and moment analysis
        
        Args:
            image_series: 3D array (frames, height, width)
        
        Returns:
            (rotation_score, affected_frame_indices)
        """
        self._log("Analyzing rotation motion...")
        
        if image_series.ndim != 3 or image_series.shape[0] < 2:
            return 0.0, []
        
        frames = image_series.shape[0]
        correlations = []
        
        # Compare each frame to reference (first frame)
        reference = image_series[0].astype(np.float32)
        reference = reference / (np.max(reference) + 1e-6)
        
        for i in range(1, frames):
            frame = image_series[i].astype(np.float32)
            frame = frame / (np.max(frame) + 1e-6)
            
            # 2D correlation coefficient
            correlation = np.corrcoef(reference.flatten(), frame.flatten())[0, 1]
            correlations.append(correlation)
        
        correlations = np.array(correlations)
        
        # Low correlation indicates rotation or significant change
        threshold_correlation = 0.85
        affected_frames = [i+1 for i, c in enumerate(correlations) 
                          if (not np.isnan(c)) and c < threshold_correlation]
        
        # Score: higher drop in correlation = more rotation
        max_correlation_drop = max(0, 1.0 - np.min(correlations)) if len(correlations) > 0 else 0
        rotation_score = min(100, (max_correlation_drop * 100))
        
        self._log(f"  Min correlation: {np.min(correlations):.3f}")
        self._log(f"  Affected frames: {len(affected_frames)}/{frames-1}")
        self._log(f"  Rotation score: {rotation_score:.1f}")
        
        return rotation_score, affected_frames
    
    def detect_pulsatile_motion(self, image_series: np.ndarray) -> Tuple[float, List[int]]:
        """
        Detect periodic motion (cardiac, respiratory) using temporal frequency analysis
        
        Args:
            image_series: 3D array (frames, height, width)
        
        Returns:
            (pulsatile_score, affected_frame_indices)
        """
        self._log("Analyzing pulsatile motion...")
        
        if image_series.ndim != 3 or image_series.shape[0] < 8:
            return 0.0, []
        
        frames, height, width = image_series.shape
        
        # Calculate mean intensity over spatial dimensions for each frame
        temporal_signal = np.mean(image_series, axis=(1, 2))
        
        # Remove baseline trend
        baseline = signal.savgol_filter(temporal_signal, 
                                       window_length=min(7, frames//2 if frames//2 > 0 else 1),
                                       polyorder=2)
        detrended = temporal_signal - baseline
        
        # Perform FFT to detect periodic components
        fft_vals = np.abs(fft.fft(detrended))
        frequencies = fft.fftfreq(len(detrended))
        
        # Look for peaks in physiological frequency range
        # Cardiac: 0.8-2 Hz, Respiratory: 0.1-0.4 Hz
        # Normalized frequency units
        phys_freq_range = (frequencies > 0.05) & (frequencies < 0.5)
        
        if np.any(phys_freq_range):
            max_phys_power = np.max(fft_vals[phys_freq_range])
            total_power = np.sum(fft_vals)
            pulsatile_ratio = (max_phys_power / total_power) * 100 if total_power > 0 else 0
            pulsatile_score = min(100, pulsatile_ratio * 10)
        else:
            pulsatile_score = 0.0
        
        # Detect high-amplitude oscillations
        detrended_std = np.std(detrended)
        high_oscillation_frames = [i for i, val in enumerate(detrended) 
                                   if abs(val) > 2.5 * detrended_std]
        
        self._log(f"  Pulsatile ratio: {pulsatile_score:.1f}%")
        self._log(f"  High-oscillation frames: {len(high_oscillation_frames)}")
        self._log(f"  Pulsatile score: {pulsatile_score:.1f}")
        
        return pulsatile_score, high_oscillation_frames
    
    def detect_noise_motion(self, image_series: np.ndarray) -> Tuple[float, List[int]]:
        """
        Detect motion through edge/noise analysis (sharp transitions indicate motion)
        
        Args:
            image_series: 3D array (frames, height, width)
        
        Returns:
            (noise_score, affected_frame_indices)
        """
        self._log("Analyzing noise patterns...")
        
        if image_series.ndim != 3:
            return 0.0, []
        
        frames, height, width = image_series.shape
        edge_magnitudes = []
        
        for i in range(frames):
            frame = image_series[i]
            
            # Calculate edge detection (Sobel operator approximation)
            gx = np.gradient(frame, axis=0)
            gy = np.gradient(frame, axis=1)
            edge_magnitude = np.sqrt(gx**2 + gy**2)
            
            # RMS of edges
            edge_rms = np.sqrt(np.mean(edge_magnitude**2))
            edge_magnitudes.append(edge_rms)
        
        edge_magnitudes = np.array(edge_magnitudes)
        
        # Detect frames with abnormally high edge magnitude
        mean_edge = np.mean(edge_magnitudes)
        std_edge = np.std(edge_magnitudes)
        threshold = mean_edge + 2.0 * std_edge
        
        affected_frames = [i for i, mag in enumerate(edge_magnitudes) if mag > threshold]
        
        # Score: ratio of affected frames
        noise_score = (len(affected_frames) / frames) * 100
        
        self._log(f"  Mean edge magnitude: {mean_edge:.2f}")
        self._log(f"  Affected frames: {len(affected_frames)}/{frames}")
        self._log(f"  Noise score: {noise_score:.1f}")
        
        return noise_score, affected_frames
    
    def analyze_motion(self, image_series: np.ndarray, 
                       weights: Optional[Dict[str, float]] = None) -> MotionMetrics:
        """
        Comprehensive motion analysis using all detection methods
        
        Args:
            image_series: 3D array (frames, height, width)
            weights: Dictionary of detection method weights
                    {'translation': 0.25, 'rotation': 0.25, 'pulsatile': 0.25, 'noise': 0.25}
        
        Returns:
            MotionMetrics with comprehensive analysis
        """
        if weights is None:
            weights = {
                'translation': 0.25,
                'rotation': 0.25,
                'pulsatile': 0.25,
                'noise': 0.25
            }
        
        self._log("=" * 70)
        self._log("COMPREHENSIVE MOTION ANALYSIS")
        self._log("=" * 70)
        self._log(f"Input: {image_series.shape[0]} frames, {image_series.shape[1]}x{image_series.shape[2]} pixels")
        
        # Run all detection methods
        translation_score, translation_frames = self.detect_translation_motion(image_series)
        rotation_score, rotation_frames = self.detect_rotation_motion(image_series)
        pulsatile_score, pulsatile_frames = self.detect_pulsatile_motion(image_series)
        noise_score, noise_frames = self.detect_noise_motion(image_series)
        
        # Combine all affected frames
        all_affected_frames = sorted(set(translation_frames + rotation_frames + 
                                         pulsatile_frames + noise_frames))
        
        # Calculate weighted overall score
        overall_score = (
            translation_score * weights['translation'] +
            rotation_score * weights['rotation'] +
            pulsatile_score * weights['pulsatile'] +
            noise_score * weights['noise']
        )
        
        # Classify severity
        if overall_score < 15:
            severity = MotionSeverity.NONE
            confidence = 0.95
        elif overall_score < 30:
            severity = MotionSeverity.MINIMAL
            confidence = 0.85
        elif overall_score < 50:
            severity = MotionSeverity.MILD
            confidence = 0.80
        elif overall_score < 75:
            severity = MotionSeverity.MODERATE
            confidence = 0.70
        else:
            severity = MotionSeverity.SEVERE
            confidence = 0.60
        
        # Generate description and recommendations
        motion_description = self._generate_description(
            translation_score, rotation_score, pulsatile_score, noise_score
        )
        recommendations = self._generate_recommendations(severity, all_affected_frames)
        
        # Get affected slices (assuming single slice per frame)
        affected_slices = all_affected_frames
        
        return MotionMetrics(
            severity=severity,
            translation_score=translation_score,
            rotation_score=rotation_score,
            pulsatile_score=pulsatile_score,
            noise_score=noise_score,
            overall_score=overall_score,
            affected_slices=affected_slices,
            affected_frames=all_affected_frames,
            motion_description=motion_description,
            recommendations=recommendations,
            confidence=confidence
        )
    
    def _generate_description(self, trans_score: float, rot_score: float, 
                             puls_score: float, noise_score: float) -> str:
        """Generate descriptive text for motion analysis"""
        components = []
        
        if trans_score > 30:
            components.append(f"significant translation ({trans_score:.0f}%)")
        elif trans_score > 15:
            components.append(f"mild translation ({trans_score:.0f}%)")
        
        if rot_score > 30:
            components.append(f"significant rotation ({rot_score:.0f}%)")
        elif rot_score > 15:
            components.append(f"mild rotation ({rot_score:.0f}%)")
        
        if puls_score > 30:
            components.append(f"cardiac/respiratory pulsation ({puls_score:.0f}%)")
        elif puls_score > 15:
            components.append(f"minor pulsation ({puls_score:.0f}%)")
        
        if noise_score > 30:
            components.append(f"high-frequency noise/motion ({noise_score:.0f}%)")
        elif noise_score > 15:
            components.append(f"minor noise patterns ({noise_score:.0f}%)")
        
        if not components:
            return "No significant motion detected"
        
        return "Detected: " + ", ".join(components)
    
    def _generate_recommendations(self, severity: MotionSeverity, 
                                 affected_frames: List[int]) -> List[str]:
        """Generate clinical recommendations based on motion severity"""
        recommendations = []
        
        if severity == MotionSeverity.NONE:
            recommendations.append("✓ Image quality acceptable for analysis")
        
        elif severity == MotionSeverity.MINIMAL:
            recommendations.append("✓ Minimal motion detected - acceptable for analysis")
            recommendations.append("  Consider excluding frames with motion artifacts if perfusion critical")
        
        elif severity == MotionSeverity.MILD:
            recommendations.append("⚠️  Mild motion present - may affect accuracy")
            recommendations.append(f"  Affected {len(affected_frames)} frames: {affected_frames[:5]}{'...' if len(affected_frames) > 5 else ''}")
            recommendations.append("  Recommend local ROI analysis away from motion-affected areas")
            recommendations.append("  Use contralateral hemisphere for comparison")
        
        elif severity == MotionSeverity.MODERATE:
            recommendations.append("⚠️  MODERATE MOTION - Significant quality impact")
            recommendations.append(f"  Affected {len(affected_frames)}/{len(affected_frames) + 1} frames")
            recommendations.append("  Recommend REPEAT STUDY with better patient stabilization")
            recommendations.append("  If repeat not possible, exclude affected regions from analysis")
            recommendations.append("  Low confidence in automated categorization")
        
        else:  # SEVERE
            recommendations.append("⛔ SEVERE MOTION - Study is COMPROMISED")
            recommendations.append(f"  {len(affected_frames)} frames affected by significant motion")
            recommendations.append("  ❌ NOT SUITABLE for perfusion analysis")
            recommendations.append("  MANDATORY: Repeat imaging with immobilization")
            recommendations.append("  Clinical correlation essential - do not rely on measurements")
        
        return recommendations
    
    def generate_report(self, metrics: MotionMetrics, patient_id: str = "UNKNOWN") -> str:
        """Generate detailed motion analysis report"""
        report = []
        report.append("=" * 80)
        report.append("CT PERFUSION - MOTION ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"\nPatient ID: {patient_id}")
        report.append(f"Analysis Date: {__import__('datetime').datetime.now()}")
        report.append(f"\nOVERALL MOTION ASSESSMENT")
        report.append("-" * 80)
        report.append(f"Severity: {metrics.severity.value}")
        report.append(f"Overall Motion Score: {metrics.overall_score:.1f}/100")
        report.append(f"Confidence in Assessment: {metrics.confidence:.0%}")
        
        report.append(f"\nDETAILED MOTION COMPONENT SCORES")
        report.append("-" * 80)
        report.append(f"Translation Motion:    {metrics.translation_score:6.1f}/100")
        report.append(f"Rotation Motion:       {metrics.rotation_score:6.1f}/100")
        report.append(f"Pulsatile Motion:      {metrics.pulsatile_score:6.1f}/100")
        report.append(f"Noise/High-Freq:       {metrics.noise_score:6.1f}/100")
        
        report.append(f"\nMOTION DESCRIPTION")
        report.append("-" * 80)
        report.append(metrics.motion_description)
        
        if metrics.affected_frames:
            report.append(f"\nAFFECTED FRAMES: {len(metrics.affected_frames)} out of multiple")
            frame_str = str(metrics.affected_frames[:10])
            if len(metrics.affected_frames) > 10:
                frame_str = frame_str[:-1] + ", ...]"
            report.append(f"  {frame_str}")
        
        report.append(f"\nCLINICAL RECOMMENDATIONS")
        report.append("-" * 80)
        for i, rec in enumerate(metrics.recommendations, 1):
            report.append(f"{i}. {rec}")
        
        report.append("\n" + "=" * 80)
        report.append("NOTES:")
        report.append("- This is an automated analysis - must be validated by radiologist")
        report.append("- Motion can invalidate perfusion measurements")
        report.append("- For severe motion, repeat imaging is strongly recommended")
        report.append("=" * 80 + "\n")
        
        return "\n".join(report)


def main():
    """Example usage"""
    print("CT Perfusion - Motion Detection Tool")
    print("=" * 70)
    
    # Create sample perfusion data (4D: frames, z-slices, height, width)
    print("\nGenerating sample perfusion data...\n")
    
    np.random.seed(42)
    n_frames = 50
    height, width = 256, 256
    
    # Create synthetic perfusion data
    base_image = np.random.normal(40, 10, (height, width))
    
    # Create series with controlled motion
    image_series = []
    for frame in range(n_frames):
        # Add translation motion
        if frame > 20:
            shift_x = int(3 * np.sin(frame * 0.1))
            shift_y = int(3 * np.cos(frame * 0.1))
        else:
            shift_x, shift_y = 0, 0
        
        # Create frame with motion
        frame_data = np.roll(base_image, (shift_y, shift_x), axis=(0, 1))
        
        # Add some noise
        frame_data += np.random.normal(0, 5, (height, width))
        
        image_series.append(frame_data)
    
    image_series = np.array(image_series)
    
    # Analyze motion
    detector = MotionDetector(verbose=True)
    metrics = detector.analyze_motion(image_series)
    
    # Generate report
    report = detector.generate_report(metrics, "DEMO_PATIENT")
    print("\n" + report)
    
    # Save report
    report_file = Path("/Users/gsharma/Programming/supreme-umbrella/motion_analysis_report.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_file}\n")


if __name__ == "__main__":
    main()
