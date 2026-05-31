---
title: "ชุดข้อมูลสารเมตาบอไลต์ NMR สำหรับเปรียบเทียบผู้ป่วย"
track: "Phenome"
domain:
  - "Metabolomics"
  - "Biomarker Discovery"
source:
  - "สถาบันฟีโนมแห่งชาติ"
total_records: null
sampled_records: 486
filetype:
  - "tsv"

---

# ชุดข้อมูลสารเมตาบอไลต์ NMR สำหรับเปรียบเทียบผู้ป่วย

## คำอธิบาย
ชุดข้อมูลผลลัพธ์การวิเคราะห์ NMR ที่เปรียบเทียบระหว่าง **ผู้ป่วยเบาหวาน + ความดันโลหิตสูง** กับ **กลุ่มควบคุม** ข้อมูลประกอบด้วย:
1. **NMR Results**: ผลการระบุสารประกอบและปริมาณ (abundance) ที่พบในแต่ละตัวอย่าง
2. **Sample Table**: ข้อมูลเมตาของแต่ละตัวอย่าง (demographics, sample type, condition)

ข้อมูลนี้มีมากกว่า **20,000 คอลัมน์** ของสัญญาณสารประกอบ (metabolite abundance) พร้อมข้อมูลกายภาพ (อายุ น้ำหนัก ส่วนสูง) และผลการวินิจฉัย

## ฟิลด์ข้อมูล

### Domain_2_NMR_results_MTBLS242.tsv
ผลการระบุสารประกอบและ abundance
| ฟิลด์ | คำอธิบาย |
|-------|----------|
| `database_identifier` | ตัวระบุสารประกอบในฐานข้อมูล |
| `chemical_formula` | สูตรเคมี |
| `smiles` | SMILES string |
| `inchi` | InChI string |
| `metabolite_identification` | ผลการระบุสารเมตาบอไลต์ |
| `chemical_shift` | ตำแหน่ง chemical shift |
| `multiplicity` | รูปแบบสัญญาณ (singlet, doublet ฯลฯ) |
| `reliability` | ค่าความน่าเชื่อถือของการระบุ |
| `smallmolecule_abundance_sub` | ปริมาณ small molecule |
| `smallmolecule_abundance_stdev_sub` | ส่วนเบี่ยงเบนมาตรฐาน |
| `0_0001_S`, `0_0002_S`, ... | ปริมาณสารในแต่ละตัวอย่าง |

### Domain_2_sample_table_MTBLS242.tsv
ข้อมูลเมตาของแต่ละตัวอย่าง
| ฟิลด์ | คำอธิบาย |
|-------|----------|
| `Source Name` | ชื่อแหล่งข้อมูล |
| `Sample Name` | ชื่อตัวอย่าง |
| `Characteristics[Organism]` | ข้อมูลสิ่งมีชีวิต |
| `Characteristics[Sample type]` | ประเภทตัวอย่าง |
| `Factor Value[time point]` | เวลาที่เก็บตัวอย่าง |

## โครงสร้างไฟล์
| ไฟล์ | รูปแบบ |
|------|--------|
| [`Domain_2_NMR_results_MTBLS242.tsv`](Domain_2_NMR_results_MTBLS242.tsv) | TSV |
| [`Domain_2_sample_table_MTBLS242.tsv`](Domain_2_sample_table_MTBLS242.tsv) | TSV |

## โจทย์ / แนวทางวิเคราะห์
- **Biomarker Discovery**: ระบุ Biomarker จำนวนน้อยที่สุดที่วินิจฉัยได้แม่นยำ
- **Predictive Model**: สร้างแบบจำลองพยากรณ์โรคจากสารเมตาบอไลต์
- **Differential Analysis**: เปรียบเทียบสารเมตาบอไลต์ระหว่างผู้ป่วย vs กลุ่มควบคุม
- **Correlation Analysis**: ความสัมพันธ์ระหว่างสารเมตาบอไลต์กับข้อมูลกายภาพ (อายุ น้ำหนัก ฯลฯ)
- **Feature Selection**: เลือกสารเมตาบอไลต์ที่สำคัญที่สุด

## Data Pipeline ที่เพิ่ม

ไฟล์ [`nmr_pipeline.py`](nmr_pipeline.py) เป็น pipeline สำหรับเตรียมข้อมูลและทำ baseline analysis แบบรันซ้ำได้:

1. โหลด `Domain_2_NMR_results_MTBLS242.tsv` และ `Domain_2_sample_table_MTBLS242.tsv`
2. แปลงตาราง NMR จากรูปแบบ metabolite x sample เป็น sample x metabolite
3. รวม abundance features เข้ากับ sample metadata ด้วย `Sample Name`
4. สร้างรายงาน QC และ feature dictionary
5. ทำ differential analysis ระหว่าง `preop` กับ sample หลังผ่าตัดทั้งหมด
6. สร้าง logistic regression baseline model สำหรับจำแนก `preop` vs `not_preop`

รัน pipeline:

```bash
python3 nmr_pipeline.py
```

ผลลัพธ์จะถูกเขียนไว้ที่โฟลเดอร์ `outputs/`:

| ไฟล์ | คำอธิบาย |
|------|----------|
| `nmr_sample_feature_matrix.csv` | ตารางหลักระดับ sample พร้อม metadata และ metabolite abundance 21 features |
| `metabolite_feature_dictionary.csv` | mapping ระหว่าง `feature_id` กับชื่อสาร / CHEBI / metadata ของสาร |
| `qc_feature_summary.csv` | missing rate, zero rate, mean, std, min, median, max ของแต่ละ feature |
| `differential_preop_vs_postop.csv` | Welch t-test, Mann-Whitney U test และ FDR q-value สำหรับ `preop` vs `not_preop` |
| `model_feature_coefficients.csv` | coefficient ของ logistic regression เรียงตามความสำคัญ |
| `pipeline_summary.json` | summary ของ pipeline, target distribution, model metrics และ note สำคัญ |

หมายเหตุจากข้อมูลจริง: ใน `Domain_2_sample_table_MTBLS242.tsv` ยังไม่พบคอลัมน์ diagnosis/control ที่มีค่าใช้งานได้ ดังนั้น pipeline นี้จึงใช้ `Factor Value[time point]` เป็น target ชั่วคราว โดยเปรียบเทียบ `preop` กับกลุ่มหลังผ่าตัดทั้งหมด หากมีไฟล์ clinical label เพิ่ม สามารถรันใหม่ด้วย target อื่นได้:

```bash
python3 nmr_pipeline.py --target-col "ชื่อคอลัมน์ target" --baseline-label "ชื่อกลุ่ม baseline"
```

## หมายเหตุ
- ข้อมูลเชื่อมโยงกับโครงการ MTBLS242
- ข้อมูลผู้ป่วย: เบาหวาน + ความดันโลหิตสูง vs. กลุ่มควบคุม
