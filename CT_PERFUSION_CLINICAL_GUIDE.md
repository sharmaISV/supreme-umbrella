# Brain CT Perfusion Post-Processing: Clinical Guide

## ⚠️ CRITICAL DISCLAIMERS

1. **This tool is for RESEARCH and EDUCATIONAL purposes ONLY**
2. **NOT approved for clinical diagnostics without radiologist review**
3. **All automated results must be validated by qualified neuroradiologists**
4. **Do NOT make clinical decisions based solely on automated analysis**
5. **Patient safety is paramount - when in doubt, consult specialists**

---

## Understanding CT Perfusion Parameters

### Primary Metrics

#### Cerebral Blood Flow (CBF)
- **Definition**: Volume of blood flowing through brain tissue per unit time
- **Units**: mL/100g/min
- **Normal Range**: 40-80 mL/100g/min
- **Clinical Significance**:
  - **High CBF**: Hyperperfusion (reperfusion, hyperemia)
  - **Low CBF**: Hypoperfusion (stenosis, stroke, reduced demand)
  - **Critical threshold**: <10 mL/100g/min suggests infarction

#### Cerebral Blood Volume (CBV)
- **Definition**: Total blood volume in tissue
- **Units**: mL/100g
- **Normal Range**: 3-8 mL/100g
- **Clinical Significance**:
  - Autoregulation compensation mechanism
  - May be increased even with reduced CBF (collateral circulation)

#### Mean Transit Time (MTT)
- **Definition**: Average time for blood to traverse the capillary bed
- **Units**: Seconds
- **Normal Range**: 3-4.5 seconds
- **Clinical Significance**:
  - Prolonged MTT = circulation delay
  - Indicates compromised perfusion
  - **Penumbra**: Area with prolonged MTT but viable tissue

#### Time to Peak (TTP)
- **Definition**: Time from arrival to maximum concentration
- **Units**: Seconds
- **Normal Range**: 4-5 seconds
- **Clinical Significance**:
  - **Delayed TTP**: Circulation delay, possible occlusion upstream
  - Best for identifying mismatch areas in stroke

---

## Processing Steps & Best Practices

### Step 1: Image Quality Assessment

**What to Check:**
- Motion artifacts (patient movement during acquisition)
- Beam hardening (metal artifacts near dental work, implants)
- Noise levels
- Proper head positioning
- Contrast bolus quality

**How to Handle:**
- If motion artifact detected: Mark as unreliable, recommend re-scan
- If beam hardening present: Flag region, exclude from analysis
- If noise too high: Lower confidence score

### Step 2: Artifact Detection

**Types of Artifacts:**

1. **Motion Artifacts**
   - Caused by: Patient movement, swallowing, head rotation
   - Recognition: Blurred edges, ghosting, streaking
   - Impact: Invalidates perfusion measurements
   - Fix: Re-scan patient with better stabilization

2. **Beam Hardening Artifacts**
   - Caused by: Dense structures (bone, metal)
   - Recognition: Dark streaks in image
   - Impact: Local measurement errors
   - Fix: Exclude affected region from analysis

3. **Contrast Bolus Artifacts**
   - Caused by: Improper timing, venous contamination
   - Recognition: Early venous enhancement, missing arterial phase
   - Impact: Unreliable time-series data
   - Fix: Verify timing; consider repeat study

### Step 3: Region of Interest (ROI) Selection

**Key Considerations:**

- **Use anatomical landmarks**: Major vascular territories
- **Standard regions**:
  - Middle Cerebral Artery (MCA) - anterior temporal lobe
  - Anterior Cerebral Artery (ACA) - medial frontal
  - Posterior Cerebral Artery (PCA) - occipital, temporal
  - Vertebral/Basilar - brainstem, cerebellum

- **Always sample contralateral hemisphere**: For comparison
- **Avoid partial volume effects**: Don't include skull, CSF
- **Size matters**: ROI should have sufficient pixels (>50-100)

### Step 4: Threshold Validation

**Important Variations:**

Perfusion values vary based on:

1. **Scanner Manufacturer**
   - GE: Different reconstruction algorithms than Siemens/Philips
   - Software versions: Updates may change calculated values
   - **Action**: Establish local baseline values for your scanner

2. **Patient Factors**
   - Age: CBF decreases ~5-7% per decade
   - Hemodynamics: Blood pressure affects perfusion
   - Cardiac output: Reduced output lowers perfusion
   - Hematocrit: Low hemoglobin increases CBV
   - Anesthesia/medication: Affects cerebral autoregulation
   - **Action**: Adjust thresholds for patient-specific factors

3. **Clinical Context**
   - Acute stroke: Different thresholds than chronic disease
   - Tumor: Hyperperfusion expected
   - Vasospasm: Severe hypoperfusion
   - **Action**: Always consider clinical history

### Step 5: Results Categorization

**Classification Logic:**

```
NORMAL
├─ CBF: 40-80 mL/100g/min
├─ CBV: 3-8 mL/100g
└─ MTT: <4.5 seconds

HYPOPERFUSED
├─ CBF: 30-40 mL/100g/min
├─ Normal or elevated CBV (autoregulation)
└─ Prolonged MTT

SEVERELY HYPOPERFUSED (ACUTE INFARCTION)
├─ CBF: <10 mL/100g/min
├─ Reduced CBV
└─ Prolonged MTT

HYPERPERFUSED
├─ CBF: >100 mL/100g/min
├─ Elevated CBV
└─ Normal/shortened MTT
└─ Causes: Reperfusion, seizure, fever
```

---

## Important Clinical Considerations

### 1. CBF-CBV Mismatch (Critical!)
- **Mismatch Pattern**: Low CBF but normal/high CBV
- **Meaning**: Collateral circulation attempting compensation
- **Action**: Indicates tissue at risk; needs intervention consideration

### 2. CBF-MTT Mismatch
- **Pattern**: Prolonged MTT but preserved CBF
- **Meaning**: Preserved tissue (collaterals maintaining flow)
- **Action**: Represents penumbra; still salvageable tissue

### 3. Comparison to Contralateral Hemisphere
- **Most important principle**: Asymmetry matters more than absolute values
- **Recommendation**: >20% asymmetry warrants investigation
- **Relative thresholds**: More reliable than absolute values

### 4. Acute Stroke Considerations

**Timing Matters:**
- **<6 hours**: Penumbra may still be salvageable
- **6-24 hours**: Extended window therapy consideration
- **>24 hours**: Likely completed infarction

**Perfusion Deficit Patterns:**
- Small CBF deficit with large MTT delay = good prognosis
- Large CBF deficit with reduced CBV = likely infarction

### 5. Seizure Distinction
- Seizure: Hyperperfusion with normal MTT
- Stroke: Hypoperfusion with prolonged MTT
- **Clinical correlation essential**

---

## Cautions & Safety Checks

### Before Analysis
- [ ] Verify patient identification
- [ ] Confirm imaging is brain CT (not CTA, CTV)
- [ ] Check timing of acquisition (post-stroke timing critical)
- [ ] Review scout images for proper positioning
- [ ] Check for contraindications in patient history

### During Analysis
- [ ] Check for all artifact types
- [ ] Verify ROI placement on multiple slices
- [ ] Compare bilateral regions
- [ ] Look for unexpected patterns
- [ ] Document confidence scores

### After Analysis
- [ ] Review final results for plausibility
- [ ] Check for internal consistency
- [ ] Compare with clinical presentation
- [ ] Flag any discordant findings
- [ ] Obtain radiologist validation

### Quality Assurance
- [ ] Never rely on automated results alone
- [ ] Always include radiologist in loop
- [ ] Maintain audit trail of decisions
- [ ] Track false positive/negative rate
- [ ] Regular training updates on new findings

---

## Recommended Thresholds by Scenario

### Acute Stroke Evaluation (6 hours)
```
Normal perfusion:
- CBF: 45-80 mL/100g/min
- CBV: 4-8 mL/100g
- MTT: 3-4.5 seconds
- TTP: 4-5 seconds

Penumbra (tissue at risk):
- CBF: 20-45 mL/100g/min
- MTT: 5-8 seconds
- CBF-MTT mismatch present

Core infarction:
- CBF: <10 mL/100g/min
- CBV: <2 mL/100g
- MTT: >8 seconds
```

### Chronic Vascular Disease
- Thresholds less strict (compensatory mechanisms)
- Relative asymmetry more important
- May see chronically reduced CBF tolerated

### Tumor/Mass Lesion
- Expect hyperperfusion in tumor
- Peripheral hypoperfusion (edema)
- Different categorization needed

---

## Code Usage Example

```python
from brain_ct_perfusion_processor import BrainCTPerfusionProcessor

# Initialize
processor = BrainCTPerfusionProcessor()

# Process metrics
result = processor.categorize_perfusion(
    metrics={
        'cbf': 25.0,  # mL/100g/min
        'cbv': 3.5,   # mL/100g
        'mtt': 6.2,   # seconds
        'ttp': 7.5    # seconds
    },
    region="Right MCA Territory"
)

# Generate report
report = processor.generate_report("PATIENT001", [result])
print(report)

# ALWAYS validate with radiologist before clinical use
```

---

## Red Flags & When to Escalate

- **Severe hypoperfusion** (CBF <10): Immediate neuro consultation
- **Discordant findings**: Results don't match clinical presentation
- **Extensive abnormality**: >50% of hemisphere affected
- **Bilateral changes**: Unusual, warrant investigation
- **Rapid changes**: Serial studies show deterioration
- **Technical failures**: Image quality compromised

---

## References

1. Wintermark M, et al. "Brain Perfusion CT" Lancet (2008)
2. Schaefer PW, et al. "Acute Ischemic Stroke" Radiology (2015)
3. Bivard A, et al. "Perfusion CT in Acute Stroke" Neuroradiology (2016)
4. DICOM Standards Part 16 - Content Mapping Resource

---

## Version Information
- Created: April 2026
- Purpose: Research/Educational
- Status: Beta (Not for clinical use)
- Review Status: Requires radiologist validation
