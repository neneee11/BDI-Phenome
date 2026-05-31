# Metabolic Recovery & Nutrition Follow-up Dashboard Prototype

## 1. Prototype Concept

Prototype นี้เป็น dashboard สำหรับช่วยประเมิน **metabolic recovery state** ของผู้ป่วยจากข้อมูล **NMR metabolite profile** โดยระบบจะดึงข้อมูล metabolite จาก **patient database / demo dataset / backend API** แทนการให้ user upload file เอง

ระบบใช้ **machine learning classifier** หรือ mock classifier ใน prototype เพื่อทำนายว่า patient sample มีลักษณะใกล้เคียงกับ:

- Preop-like
- Transition
- Post-op-like

จากนั้นระบบจะแสดง:

- Predicted metabolic state
- Post-op probability
- Recovery score
- Explainable biomarkers
- Nutrition follow-up flag
- LLM-generated clinical decision-support summary

> สำคัญ: แอปนี้เป็น **clinical decision-support tool** ไม่ใช่ระบบวินิจฉัยโรค ไม่ใช่ระบบสั่งอาหารรักษา และไม่ใช่ระบบแทนแพทย์หรือนักกำหนดอาหาร

---

## 2. Main Workflow

```text
Select Patient / Demo Case
        ↓
Fetch NMR metabolite profile from database
        ↓
Preprocess metabolites
        ↓
ML prediction
        ↓
Recovery score
        ↓
Explainable biomarkers
        ↓
LLM-generated interpretation
        ↓
Nutrition follow-up suggestion
```

---

## 3. Data Input: Patient Selection Instead of Upload

Prototype นี้ไม่ต้องมี upload CSV ในหน้าแรก แต่ให้ user เลือก patient sample จาก list หรือ dropdown

### Suggested UI

**Select Patient Sample**

| Patient ID | Visit | NMR Status | Action |
|---|---|---|---|
| P001 | Pre-op | NMR available | View |
| P002 | Post-op Week 1 | NMR available | View |
| P003 | Post-op Month 1 | NMR available | View |

เมื่อ user เลือก patient ระบบจะดึงข้อมูล metabolite อัตโนมัติจาก mock database หรือ backend API

---

## 4. Data Fetching

ใน prototype ให้จำลองว่าระบบดึงข้อมูลจาก backend endpoint เช่น:

```text
GET /api/patients/{patient_id}/metabolites
```

ตัวอย่าง response:

```json
{
  "patient_id": "P003",
  "visit": "Post-op Month 1",
  "sample_date": "2025-05-10",
  "metabolites": {
    "Dimethyl sulfone": 1.42,
    "L-valine": 0.63,
    "isopropanol": 0.38,
    "lipoproteins": 0.71,
    "glycine": 1.36,
    "L-leucine": 0.58
  }
}
```

ใน prototype แรกสามารถใช้ mock JSON data ใน frontend ได้ก่อน โดยยังไม่ต้องต่อ database จริง

---

## 5. Top-6 NMR Metabolites

ระบบ prototype ใช้ metabolite หลัก 6 ตัว ได้แก่:

1. Dimethyl sulfone
2. L-valine
3. isopropanol
4. lipoproteins
5. glycine
6. L-leucine

### Expected Post-op Direction

| Metabolite | Expected Post-op Direction | Interpretation |
|---|---|---|
| Dimethyl sulfone | Increased | Associated with recovery pattern |
| glycine | Increased | Associated with recovery pattern |
| L-valine | Decreased | Consistent with post-op pattern |
| L-leucine | Decreased | Consistent with post-op pattern |
| isopropanol | Decreased | Consistent with post-op pattern |
| lipoproteins | Decreased / should not remain high | Monitor lipid-related profile |

---

## 6. Preprocessing Step

หลังจากระบบดึงข้อมูลมาแล้ว ให้มี preprocessing step อัตโนมัติ

### Preprocessing Tasks

- Check missing metabolite values
- Validate ว่ามี metabolite ครบทั้ง 6 ตัว
- Normalize / scale metabolite values
- Map metabolite names ให้ตรงกับ model input
- Compare direction against expected post-op pattern

### Suggested UI Status

```text
Data fetched successfully
6 / 6 metabolites detected
Preprocessing completed
```

ถ้าข้อมูลไม่ครบ:

```text
Missing metabolite values detected. Please check patient NMR profile.
```

---

## 7. Metabolic-State Classifier

ระบบใช้ ML classifier เพื่อประเมิน metabolic state ของ patient sample

### Output Card Example

```text
Predicted State: Post-op-like
Post-op Probability: 82%
Confidence: High
```

หรือ:

```text
Predicted State: Transition
Post-op Probability: 56%
Confidence: Moderate
```

ใน prototype ถ้ายังไม่มี ML model จริง สามารถใช้ mock classifier ได้ก่อน

---

## 8. Recovery Score

Recovery Score คำนวณจากจำนวน biomarkers ที่เปลี่ยนไปในทิศทางที่คาดหวังสำหรับ post-op recovery pattern

### Score Logic

```text
For each of 6 biomarkers:
- If direction matches expected post-op pattern → +1 score
- If direction does not match expected post-op pattern → +0 score

Total score = 0–6
```

### Score Interpretation

| Recovery Score | Interpretation |
|---:|---|
| 0–2 | Preop-like |
| 3 | Transition |
| 4–6 | Post-op-like |

### UI Example

```text
Recovery Score: 5 / 6
Status: Post-op-like
```

ควรแสดงเป็น gauge หรือ progress bar

---

## 9. Mock Probability Logic

สำหรับ prototype แรก สามารถ map score เป็น probability แบบง่ายได้

| Recovery Score | Post-op Probability |
|---:|---:|
| 0 / 6 | 20% |
| 1 / 6 | 30% |
| 2 / 6 | 40% |
| 3 / 6 | 55% |
| 4 / 6 | 68% |
| 5 / 6 | 82% |
| 6 / 6 | 92% |

ตัวอย่าง:

```text
Recovery Score = 5 / 6
Predicted State = Post-op-like
Post-op Probability = 82%
```

---

## 10. Explainable Biomarkers

Section นี้ต้องอธิบายว่า biomarker ตัวไหนสนับสนุนผล prediction และตัวไหนยังต้องติดตาม

### Example Checklist

```text
✓ Dimethyl sulfone increased
✓ glycine increased
✓ L-valine decreased
✓ L-leucine decreased
✓ isopropanol decreased
✗ lipoproteins still high
```

### Suggested Explanation

```text
Most biomarkers are moving in the expected post-op recovery direction.
Lipoproteins remain elevated and should be monitored in follow-up.
```

ส่วนนี้ช่วยให้ระบบไม่เป็น black box และช่วยให้ clinician / dietitian เห็นเหตุผลของ prediction

---

## 11. Nutrition Follow-up Flag

ระบบควรแสดง badge สีเพื่อบอกระดับ follow-up

### Case 1: Low Risk

ใช้เมื่อ recovery score สูง เช่น 4–6 และไม่มี biomarker ที่น่ากังวลมาก

```text
Low Risk
Routine follow-up
```

### Suggested Follow-up

```text
- Continue routine nutrition follow-up
- Monitor lipid-related profile at next visit
- Check metabolic recovery trend over time
```

---

### Case 2: Needs Review

ใช้เมื่อ recovery score ต่ำ เช่น 0–3 หรือมี biomarker ที่ยังน่าติดตาม เช่น lipoproteins still high

```text
Needs Review
Recommend dietitian follow-up
```

### Suggested Follow-up

```text
- Review protein intake pattern
- Monitor lipid-related profile
- Check metabolic recovery trend at next visit
- Consider dietitian consultation if score remains low
```

---

## 12. Wording Rules for Nutrition Suggestion

ห้ามเขียนให้เหมือนระบบสั่งการรักษาหรือสั่งอาหารโดยตรง

### Avoid

```text
Prescribe high-protein diet
Give low-fat diet
Treat patient with nutrition plan
```

### Use Instead

```text
Review protein intake pattern
Monitor lipid-related profile
Consider dietitian consultation
Suggest routine follow-up
Flag for nutrition review
```

ภาษาควรเป็น decision support เท่านั้น ไม่ใช่ treatment recommendation

---

## 13. LLM Layer

สามารถใส่ LLM ในแอปได้ แต่ LLM ไม่ควรเป็นตัวทำนายผลหลัก และไม่ควรเป็นตัวตัดสิน clinical decision

บทบาทของ LLM คือเป็น **explanation and reporting layer**

### LLM Input

LLM รับข้อมูลที่ผ่าน model แล้ว เช่น:

```json
{
  "patient_id": "P003",
  "visit": "Post-op Month 1",
  "predicted_state": "Post-op-like",
  "postop_probability": 0.82,
  "recovery_score": "5/6",
  "biomarker_findings": [
    "Dimethyl sulfone increased",
    "glycine increased",
    "L-valine decreased",
    "L-leucine decreased",
    "isopropanol decreased",
    "lipoproteins still high"
  ],
  "nutrition_flag": "Low Risk"
}
```

### LLM Output Example

```text
Clinical Decision-Support Summary

Patient P003 shows a post-op-like metabolic recovery pattern. The model estimates an 82% probability of a post-op metabolic state with a recovery score of 5 out of 6. Most biomarkers are moving in the expected recovery direction, including increased Dimethyl sulfone and glycine, and decreased L-valine, L-leucine, and isopropanol. Lipoproteins remain elevated and should be monitored in follow-up.

Suggested Follow-up

Routine nutrition follow-up is suggested. Continue monitoring lipid-related profile and reassess metabolic recovery trend at the next visit.
```

### Safety Note

```text
The LLM does not diagnose, prescribe, or make treatment decisions. It only summarizes structured model outputs into readable decision-support text for healthcare professionals.
```

---

## 14. Suggested Dashboard Layout

Dashboard แบ่งเป็น 7 sections

### 1. Select Patient Sample

- Patient dropdown / patient list
- Load data button
- Status: NMR available / unavailable

### 2. Patient Metadata

- Patient ID
- Visit
- Sample date
- NMR status

### 3. NMR Metabolite Profile

Table แสดง top-6 metabolites

| Metabolite | Value | Expected Direction | Patient Trend |
|---|---:|---|---|
| Dimethyl sulfone | 1.42 | Increase | Increased |
| glycine | 1.36 | Increase | Increased |
| L-valine | 0.63 | Decrease | Decreased |
| L-leucine | 0.58 | Decrease | Decreased |
| isopropanol | 0.38 | Decrease | Decreased |
| lipoproteins | 0.71 | Decrease | Still high |

### 4. Metabolic-State Classifier

Card แสดง:

```text
Predicted State: Post-op-like
Post-op Probability: 82%
```

### 5. Recovery Score

Gauge / progress bar:

```text
Recovery Score: 5 / 6
Status: Post-op-like
```

### 6. Explainable Biomarkers

Checklist:

```text
✓ Dimethyl sulfone increased
✓ glycine increased
✓ L-valine decreased
✓ L-leucine decreased
✓ isopropanol decreased
✗ lipoproteins still high
```

### 7. Nutrition Follow-up + LLM Summary

- Badge: Low Risk / Needs Review
- Suggested follow-up list
- LLM-generated clinical summary
- Safety note

---

## 15. Suggested Frontend Components

ถ้าทำด้วย React / Next.js สามารถแบ่ง component ได้แบบนี้:

```text
/components
  PatientSelector.tsx
  PatientMetadataCard.tsx
  MetaboliteTable.tsx
  PredictionCard.tsx
  RecoveryGauge.tsx
  BiomarkerChecklist.tsx
  NutritionFlagCard.tsx
  LLMSummaryCard.tsx
  DisclaimerBanner.tsx
```

---

## 16. Example Mock Data

```js
const demoPatients = [
  {
    patientId: "P001",
    visit: "Pre-op",
    sampleDate: "2025-04-01",
    metabolites: {
      "Dimethyl sulfone": 0.72,
      "L-valine": 1.28,
      "isopropanol": 1.12,
      "lipoproteins": 1.35,
      "glycine": 0.68,
      "L-leucine": 1.21
    }
  },
  {
    patientId: "P002",
    visit: "Post-op Week 1",
    sampleDate: "2025-04-18",
    metabolites: {
      "Dimethyl sulfone": 1.02,
      "L-valine": 0.92,
      "isopropanol": 0.78,
      "lipoproteins": 1.05,
      "glycine": 1.01,
      "L-leucine": 0.88
    }
  },
  {
    patientId: "P003",
    visit: "Post-op Month 1",
    sampleDate: "2025-05-10",
    metabolites: {
      "Dimethyl sulfone": 1.42,
      "L-valine": 0.63,
      "isopropanol": 0.38,
      "lipoproteins": 0.71,
      "glycine": 1.36,
      "L-leucine": 0.58
    }
  }
];
```

---

## 17. Prototype Logic Pseudocode

```text
1. User selects patient sample
2. App fetches metabolite profile from mock dataset or backend API
3. App validates top-6 metabolites
4. App preprocesses / normalizes values
5. App compares each metabolite against expected post-op direction
6. App calculates recovery score from 0 to 6
7. App maps recovery score to predicted state and probability
8. App generates explainable biomarker checklist
9. App assigns nutrition follow-up flag
10. App sends structured output to LLM
11. LLM generates clinical decision-support summary
12. Dashboard displays final result
```

---

## 18. Key Message for Team

```text
Prototype นี้จะเป็น NMR metabolite-based recovery decision-support dashboard โดย user ไม่ต้อง upload file แต่เลือก patient sample จาก list หรือ demo dataset จากนั้นระบบจะดึงข้อมูล top-6 metabolites จากฐานข้อมูลหรือ mock API แล้วนำไป preprocess และประเมินด้วย ML classifier หรือ mock classifier

ผลลัพธ์จะแสดงเป็น predicted state, post-op probability, recovery score, explainable biomarker checklist และ nutrition follow-up flag

LLM จะใช้เป็น explanation layer เพื่อสรุปผลให้อ่านง่ายสำหรับทีม healthcare professionals โดย LLM ไม่ได้วินิจฉัย ไม่ได้ prescribe diet และไม่ได้ตัดสิน clinical decision เอง ระบบนี้เน้น decision support เพื่อช่วย prioritize nutrition follow-up อย่างปลอดภัย
```

---

## 19. One-liner

```text
This prototype is an NMR metabolite-based recovery decision-support dashboard that fetches patient metabolite profiles from a database, predicts post-op-like metabolic recovery, explains key biomarker changes, and uses an LLM to generate safe nutrition follow-up summaries for healthcare professionals.
```

ภาษาไทย:

```text
Prototype นี้เป็น dashboard สำหรับช่วยประเมิน metabolic recovery จาก NMR metabolite profile โดยดึงข้อมูลจาก patient database ใช้ ML ประเมินภาวะ preop/post-op-like อธิบาย biomarker ที่เกี่ยวข้อง และใช้ LLM ช่วยสรุปผลเพื่อสนับสนุน nutrition follow-up อย่างปลอดภัย
```

---

## 20. Disclaimer Text for UI

```text
This tool is for clinical decision support only. It is not intended for diagnosis, treatment, or prescription. Final clinical decisions should be made by qualified healthcare professionals.
```

ภาษาไทย:

```text
เครื่องมือนี้ใช้เพื่อสนับสนุนการตัดสินใจทางคลินิกเท่านั้น ไม่ใช่ระบบวินิจฉัย รักษา หรือสั่งอาหาร/ยา การตัดสินใจขั้นสุดท้ายควรทำโดยบุคลากรทางการแพทย์ที่มีคุณสมบัติเหมาะสม
```
