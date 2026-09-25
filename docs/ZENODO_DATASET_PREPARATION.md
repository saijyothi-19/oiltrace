# OILTRACE — Zenodo Sentinel-1 SAR Oil Spill Dataset Preparation Guide

This guide details how to acquire, structure, preprocess, and validate real **Sentinel-1 SAR oil spill imagery** for training the OILTRACE supervised U-Net deep learning model (SIH26143).

---

## 1. Where Raw Zenodo Images and Masks Go

Place your downloaded raw Sentinel-1 GeoTIFF scenes and ground-truth masks into an input folder (e.g. `data/raw_zenodo/`):

```text
data/raw_zenodo/
├── images/
│   ├── s1_scene_01.tif        <- 2048x2048 (or 2048x2048x2 VV/VH) Sentinel-1 GeoTIFF
│   ├── s1_scene_02.tif
│   └── ...
└── masks/
    ├── s1_scene_01.png        <- 2048x2048 ground-truth mask (0=sea, 1 or 255=spill)
    ├── s1_scene_02.png
    └── ...
```

*Note: Filenames must match between `images/` and `masks/` (e.g. `s1_scene_01.tif` pairs with `s1_scene_01.png`, `s1_scene_01.tif`, or `s1_scene_01_mask.png`).*

---

## 2. Key Processing Guarantees

1. **Exact 1:1 Spatial Alignment**: The raw $2048 \times 2048$ SAR swath is **never blindly resized**. It is synchronously tiled into $256 \times 256$ sub-patches.
2. **Polarization Extraction**: Automatically extracts the co-polarized **VV channel** (channel 0) which exhibits the strongest capillary wave dampening contrast.
3. **Radiometric Calibration**: Calibrates SAR Digital Numbers (DN) to Sigma Naught ($\sigma^0$) backscatter decibels (dB), clips to marine dynamic range $[-30.0, 0.0]\text{ dB}$, and normalizes to $[0.0, 1.0]$.
4. **Binary Masks**: Converts all ground truth labels to $0$ (clean sea surface) and $255$ (oil spill).
5. **Leakage-Free Splitting**: Dataset splitting (70% train, 20% val, 10% test) is performed at the **original 2048×2048 scene level**. Patches from the same scene are never divided across training and validation sets.
6. **False-Positive Suppression**: Retains a balanced sample of negative (clean water) patches alongside positive spill patches so the U-Net learns to suppress sea clutter.

---

## 3. How to Run Dry-Run Mode

Before writing thousands of image patches, run the dry-run command to test file pairing, integrity, dimension matching, and patch generation without writing to disk:

```bash
python scripts/prepare_zenodo_dataset.py \
  --input-dir data/raw_zenodo \
  --output-dir data/dataset \
  --max-scenes 2 \
  --dry-run
```

The terminal will display the number of positive/negative patches, scene-level split statistics, and verify that there are zero NaNs or corruption errors.

---

## 4. How to Run Full Dataset Preparation

Once the dry-run confirms that your raw files are valid, run the full conversion pipeline:

```bash
python scripts/prepare_zenodo_dataset.py \
  --input-dir data/raw_zenodo \
  --output-dir data/dataset \
  --tile-size 256 \
  --stride 256 \
  --polarization VV \
  --negative-ratio 1.0 \
  --train-split 0.70 \
  --val-split 0.20 \
  --seed 42
```

This generates the final model-ready structure:
```text
data/dataset/
├── train/
│   ├── images/
│   └── masks/
├── val/
│   ├── images/
│   └── masks/
└── test/
    ├── images/
    └── masks/
```

---

## 5. How to Validate the Resulting Dataset

Run the official OILTRACE dataset validator to ensure 100% compliance before starting training:

```bash
python ml/training/train_unet.py --validate-only --data-dir data/dataset
```

Expected validation output:
```text
======================================================================
  OILTRACE — Deep Convolutional U-Net Training Suite (SIH26143)
  Supervised Satellite SAR Marine Oil Spill Segmentation
======================================================================

[STEP 1/4] Validating Dataset Integrity: data/dataset
  Mode:            SPLIT_STRUCTURE
  Total Images:    <TOTAL_PATCHES>
    - Split 'train': <TRAIN_COUNT> samples (Valid: True)
    - Split 'val':   <VAL_COUNT> samples (Valid: True)
    - Split 'test':  <TEST_COUNT> samples (Valid: True)
  [OK] Dataset integrity passed all checks (existence, matching dimensions, binary masks, no data leakage).
[INFO] --validate-only requested. Exiting successfully.
```
