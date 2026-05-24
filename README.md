# BDI Hackathon 20226 Sampled Dataset

ชุดข้อมูลตัวอย่างสำหรับแการข่งขัน BDI Hackathon แบ่งเป็น 7 Dataset 3 Track

## Data Overview

| ชื่อชุดข้อมูล | Track | คำอธิบาย |
|-------------|-------|----------|
| [`ชุดข้อมูลสเปกตรัม NMR สำหรับตรวจรูปแบบสารเคมี`](nmr-pattern/) | **Phenome** | **2D NMR Spectrum (PDF)** : ~20,000+ feature/ตัวอย่าง ข้อมูลดิบที่ต้องพึ่งผู้เชี่ยวชาญตีความ; ใช้ฝึก ML จำแนกสารประกอบ/ระบุ biomarker โดยลดความซับซ้อนของสัญญาณที่ซ้อนทับกัน |
| [`ชุดข้อมูลสารเมตาบอไลต์ NMR สำหรับเปรียบเทียบผู้ป่วย`](nmr-result/) | **Phenome** | **Metabolite Abundance (TSV, 486 samples, 20K+ columns)** : ค่าปริมาณสารเมตาบอไลต์ + metadata (อายุ, น้ำหนัก, การวินิจฉัย); เปรียบเทียบผู้ป่วยเบาหวาน+ความดัน vs. กลุ่มควบคุม; ใช้ค้นหา biomarker จำนวนน้อยที่สุดที่แยกโรคได้แม่นยำ |
| [`ชุดข้อมูล EMR ผู้ป่วยความดันแบบติดตามยาว`](hypertension/) | **Medical** | **Hypertension EMR (XLSX, 150K patients, sampled 100)** : ข้อมูล longitudinal แบ่ง Period ทุก 60 วันรอบวันวินิจฉัย; มี Vitalsign, Lab (HbA1c, lipid), Comorbidity, ยา (ARB/CCB/ACEI); ใช้วิเคราะห์ประสิทธิภาพยา, พยากรณ์ความเสี่ยงหัวใจ/ไต |
| [`ชุดข้อมูล EMR ผู้ป่วยเบาหวานแบบติดตามยาว`](diabetes/) | **Medical** | **Diabetes EMR (XLSX, 70K patients, sampled 100)** : ข้อมูล longitudinal แบ่ง Period ทุก 60 วัน; มี HbA1c, C-peptide, ยา (metformin/insulin/GLP-1); แบ่ง Type 1 ~2K, Type 2 ~50K, Unknown ~20K; ใช้จำแนกประเภท, พยากรณ์ HbA1c/แทรกซ้อน |
| [`ชุดข้อมูลคลื่นของเครื่องช่วยหายใจจากผู้ป่วย ICU`](ventilator/) | **Medical** | **Ventilator Waveform (CSV/JSON, 17K records)** : สัญญาณ 3 แกน (Flow/Pressure/Volume) บันทึก 25 Hz, 24 ชั่วโมง/วัน, ติดต่อกัน 2–3 สัปดาห์ + patient demographics/diagnosis/handling; ใช้ตรวจจับความผิดปกติ, พยากรณ์ ICU stay, จำแนกโหมดการช่วยหายใจ |
| [`ชุดข้อมูลสแกน 3 มิติ เมืองขอนแก่น`](3dpoints/) | **Smart City** | **3D Point Cloud / Mesh (tar.gz, 1,274 tiles, sampled 12)** : ข้อมูลสแกนเมืองขอนแก่นพร้อม texture และ metadata จัดเป็น Grid Tile; ใช้ตรวจจับวัตถุ 3D (อาคาร, ยานพาหนะ, ต้นไม้), วิเคราะห์ผังเมือง, เปรียบเทียบการเปลี่ยนแปลงพื้นที่ |
| [`ชุดข้อมูลบันทึกคำร้องจากประชาชน เทศบาลนครขอนแก่น`](complaints/) | **Smart City** | **Municipal Complaints (XLSX, 46K records, sampled 462)** : คำร้องประชาชนต่อเทศบาลนครขอนแก่น พร้อมวันที่รับ-เสร็จ, เขต/ชุมชน, สถานะ, ส่วนงาน; ใช้ NLP จัดหมวดหมู่ข้อความ, วิเคราะห์ประสิทธิภาพการแก้ปัญหา, พยากรณ์วันเสร็จ, Heatmap ความหนาแน่นตามพื้นที่ |
