# Motion Detection in CT Perfusion Data

## Overview

Automatic motion detection is critical for CT perfusion analysis because motion artifacts can:
- **Invalidate perfusion measurements** (CBF, CBV, MTT, TTP)
- **Cause false positives** (appear as hypoperfusion when it's just motion)
- **Reduce confidence** in diagnostic interpretations
- **Waste resources** if study must be repeated

This tool uses **4 complementary detection methods** to identify various types of motion:

---

## Motion Detection Methods

### 1. **Translation Motion Detection**
**What it detects:** Patient shifting in X-Y plane (left-right, up-down)

**How it works:**
- Calculates centroid (center of mass) for each frame
- Tracks frame-to-frame centroid displacement
- Flags frames with displacement >2 pixels as suspicious

**Clinical impact:**
- Causes blurring of image details
- Registration errors between time points
- 2-3 pixel shifts are still acceptable
- >5 pixel shifts indicate significant problem

**Score range:** 0-100
- 0-15: Acceptable
- 15-30: Mild
- 30+: Significant problem

---

### 2. **Rotation Motion Detection**
**What it detects:** Head rotation or tilt

**How it works:**
- Compares correlation between each frame and reference frame
- Rotational motion → lower image correlation
- Detects both small tilts and large rotations

**Clinical impact:**
- Causes registration failure between slices
- Misalignment of ROIs
- Can appear as new lesions or disappearing lesions
- Even small rotations (5-10°) significantly affect analysis

**Score range:** 0-100
- 0-15: Acceptable
- 15-30: Minor
- 30+: Problematic

---

### 3. **Pulsatile Motion Detection**
**What it detects:** Cardiac and respiratory motion patterns

**How it works:**
- Creates temporal signal: mean intensity over all pixels per frame
- Removes baseline drift
- Uses FFT to identify periodic components
- Searches for peaks in physiological frequency range (0.05-0.5 Hz)
  - Cardiac: 0.8-2 Hz (50-120 bpm)
  - Respiratory: 0.1-0.4 Hz (6-24 breaths/min)

**Clinical impact:**
- Causes "blurring" in particular directions
- More problematic at brainstem/cerebellum (close to heart)
- Less problematic for cortical regions
- Often unavoidable; acceptance depends on magnitude

**Score range:** 0-100
- 0-15: Normal physiological
- 15-30: Mild
- 30+: Excessive

---

### 4. **Noise/High-Frequency Motion Detection**
**What it detects:** High-frequency motion and switching noise

**How it works:**
- Calculates edge magnitude for each frame (Sobel operator)
- Detects frames with abnormally high edges
- Identifies motion-related high-frequency patterns

**Clinical impact:**
- Causes "grainy" appearance
- Can mask subtle lesions
- Indicates patient fidgeting or involuntary movement
- Often appears as scattered noise

**Score range:** 0-100
- 0-15: Acceptable noise level
- 15-30: Noisy but usable
- 30+: Too noisy for reliable analysis

---

## Severity Classification

### Motion Severity Levels

```
NONE (Score <15)
├─ No significant motion detected
├─ Images suitable for detailed analysis
└─ Confidence: 95%

MINIMAL (Score 15-30)
├─ Minimal motion present but acceptable
├─ May exclude specific affected frames
└─ Confidence: 85%

MILD (Score 30-50)
├─ Motion present, will impact accuracy
├─ Use local ROI away from motion areas
├─ Compare contralateral hemisphere
└─ Confidence: 80%

MODERATE (Score 50-75)
├─ Significant quality degradation
├─ Recommend REPEAT study
├─ If must analyze: exclude affected regions
└─ Confidence: 70%

SEVERE (Score >75)
├─ Study is COMPROMISED
├─ NOT suitable for clinical analysis
├─ Mandatory repeat imaging
└─ Confidence: 60%
```

---

## How to Use

### Basic Usage

```python
from motion_detector import MotionDetector
import numpy as np

# Create detector
detector = MotionDetector(verbose=True)

# Analyze perfusion series (3D array: frames, height, width)
# Example: 50 time frames, 256x256 pixels each
metrics = detector.analyze_motion(image_series)

# Generate report
report = detector.generate_report(metrics, patient_id="PATIENT001")
print(report)
```

### With Custom Weights

```python
# Adjust importance of different motion types
weights = {
    'translation': 0.30,  # More weight on translation
    'rotation': 0.20,     # Less weight on rotation
    'pulsatile': 0.30,    # Pulsatile motion important
    'noise': 0.20
}

metrics = detector.analyze_motion(image_series, weights=weights)
```

### Access Individual Scores

```python
print(f"Translation: {metrics.translation_score:.1f}")
print(f"Rotation: {metrics.rotation_score:.1f}")
print(f"Pulsatile: {metrics.pulsatile_score:.1f}")
print(f"Noise: {metrics.noise_score:.1f}")
print(f"Overall: {metrics.overall_score:.1f}")
print(f"Severity: {metrics.severity.value}")
```

---

## Interpreting Results

### What Each Score Means

**Translation Score: 80**
- Centroid shifted >4 pixels between frames
- Action: Check scanner positioning, patient movement

**Rotation Score: 50**
- Image correlation dropped ~0.5
- Action: Patient may have turned head; check scout image

**Pulsatile Score: 65**
- Strong cardiac/respiratory pattern
- Action: Depends on region; more critical for brainstem

**Noise Score: 25**
- Some frames have unusually high edge content
- Action: May indicate fidgeting; acceptable for routine analysis

---

## Important Cautions

### ⚠️ Limitations of Automated Detection

1. **Not all motion is detected**
   - Slow creep (gradual patient movement) may be missed
   - Detector tuned for frame-to-frame changes
   - Manual review still essential

2. **Contrast bolus effects can mimic motion**
   - Rapid enhancement changes look like intensity shifts
   - FFT may detect bolus as "pulsatile"
   - Always review raw images visually

3. **Normal physiological patterns included**
   - Some pulsatile motion is normal and unavoidable
   - Severity depends on clinical context
   - Mild pulsation often acceptable

4. **Correlation-based detection can fail**
   - If entire image changes (e.g., bolus arrival), correlation drops
   - May falsely flag motion during active perfusion
   - Must correlate with acquisition timing

### ✓ Best Practices

- **Always visually review** affected frames in the DICOM viewer
- **Check acquisition timing** against motion findings
- **Compare to scout image** for patient positioning
- **Use contralateral comparison** when motion present
- **Consider repeat study** if affecting clinical ROI
- **Document motion** in radiology report

---

## Clinical Decision Tree

```
Motion Detection Complete
    │
    ├─ Severity = NONE
    │   └─ ✓ Proceed with standard analysis
    │
    ├─ Severity = MINIMAL
    │   └─ ✓ Proceed with analysis
    │       Optional: Flag specific frames for exclusion
    │
    ├─ Severity = MILD
    │   └─ ⚠️  PROCEED WITH CAUTION
    │       • Use local ROI away from motion
    │       • Compare contralateral regions
    │       • Lower confidence in borderline findings
    │       • Document motion in report
    │
    ├─ Severity = MODERATE
    │   ├─ Is motion in region of interest?
    │   │   ├─ YES → ❌ RECOMMEND REPEAT
    │   │   └─ NO  → ⚠️  ANALYZE UNAFFECTED REGION
    │   └─ Document motion impact
    │
    └─ Severity = SEVERE
        ├─ ❌ NOT SUITABLE for perfusion analysis
        ├─ 🔄 MANDATORY REPEAT STUDY
        └─ Consider reposition, sedation, or re-scan
```

---

## Integration with Perfusion Processor

```python
from motion_detector import MotionDetector
from brain_ct_perfusion_processor import BrainCTPerfusionProcessor

# First: Check motion
detector = MotionDetector()
motion_metrics = detector.analyze_motion(image_series)

# Only proceed if motion acceptable
if motion_metrics.severity.name not in ['SEVERE', 'MODERATE']:
    # Then: Analyze perfusion
    processor = BrainCTPerfusionProcessor()
    perfusion_result = processor.categorize_perfusion(metrics, region)
    
    # Include motion confidence in final report
    confidence = motion_metrics.confidence
else:
    print("⛔ Motion too severe - repeat study recommended")
```

---

## Recommendations for Different Scenarios

### Acute Stroke Protocol
- Motion MUST be minimal (<30) in infarct territory
- Mild motion acceptable in contralateral hemisphere
- Consider repeat if infarct core affected by motion
- Time-sensitive: must balance quality vs. clinical timing

### Chronic Vascular Disease
- Slightly more tolerant of motion (study can wait)
- Can exclude individual slices/frames
- Focus on most clinically relevant territory

### Research/Quality Assurance
- Stricter criteria: <20 motion score acceptable
- Document all motion findings
- Use for scanner QA tracking

### Pediatric Patients
- More motion expected (difficulty cooperating)
- May require sedation for diagnostic study
- Repeat studies common

---

## References

1. Wintermark M. "Brain Perfusion-CT Applications" Neuroradiology (2006)
2. Schaefer PW. "Patient Motion Artifacts in CT" Radiology (2010)
3. Kudo K. "Perfusion Imaging Artifacts" AJNR (2015)
4. Signal Processing for Motion Detection: Nyquist Theorem, FFT fundamentals

---

## Version & Status

- **Version**: 1.0
- **Date**: April 2026
- **Status**: Research/Educational Use
- **Clinical Use**: Requires radiologist validation
- **Confidence**: 60-95% depending on motion severity

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| All frames flagged as rotated | Strong perfusion gradient | Verify motion visually |
| High pulsatile score | Normal physiology | May be acceptable |
| Intermittent high scores | Contrast bolus | Check timing, not motion |
| All scores zero | Empty/constant image | Check input data |
| Slow, gradual motion missed | Low frame-frame change | Use longer temporal window |

