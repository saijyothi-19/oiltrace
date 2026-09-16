# OILTRACE — Marine Oil Spill AI Subsystem: Technical Specification & User Guide

**Project**: OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction & Vessel Attribution System  
**Hackathon**: Smart India Hackathon 2026 (Problem Statement SIH26143)  
**Subsystem**: Marine Remote Sensing & Deep Semantic Segmentation Engine

---

> [!IMPORTANT]
> **SCIENTIFIC INTEGRITY & NON-FABRICATION POLICY**  
> OILTRACE strictly prohibits the fabrication or hardcoding of artificial model accuracy metrics. All reported evaluation figures (IoU, Dice, Precision, Recall, F1) are computed directly from validation and test rasters using empirical ground-truth masks. When working without a downloaded proprietary satellite repository, the training pipeline uses a fully reproducible synthetic SAR dataset clearly watermarked:  
> *`"Synthetic demonstration data — not real-world evidence."`*

---

## 1. Physical Foundation: SAR Remote Sensing of Ocean Oil Slicks

### 1.1 Radar Backscatter Physics
Synthetic Aperture Radar (SAR) sensors—such as Sentinel-1A and Sentinel-1B operating in C-band ($\approx 5.405\text{ GHz}$, wavelength $\lambda \approx 5.55\text{ cm}$)—detect oil spills through the interaction between radar pulses and ocean surface capillary and short gravity waves (Bragg scattering):

$$\lambda_{Bragg} = \frac{\lambda_{radar}}{2 \sin(\theta)}$$

Where $\theta$ is the radar incidence angle ($20^\circ - 45^\circ$).

- **Clean Sea Surface**: Wind-induced capillary waves generate high radar backscatter returns, appearing bright or medium grey.
- **Oil-Covered Sea Surface**: Petroleum hydrocarbons form a viscoelastic film on the water surface, drastically increasing surface tension and dampening short capillary-gravity waves (Marangoni damping). The sea surface behaves like a mirror, reflecting radar pulses away from the satellite antenna. Consequently, oil slicks appear as distinctive **dark formations**.

---

## 2. SAR Preprocessing Pipeline

Raw SAR scenes are preprocessed using a 5-stage pipeline (`ml/preprocessing/sar_preprocessor.py`):

```
+----------------+      +---------------------+      +---------------------+
| Raw SAR Raster | ---> | Decibel Calibration | ---> | Adaptive Lee Filter |
| (TIFF/PNG/NPY) |      | (Sigma-0 dB)        |      | (5x5 Speckle Red.)  |
+----------------+      +---------------------+      +---------------------+
                                                                |
                                                                v
+------------------+      +--------------------+      +--------------------+
| Model-Ready      | <--- | Sliding-Window     | <--- | Dynamic Range Norm |
| Overlapping Tiles|      | Tile Extraction    |      | [-30 dB, 0 dB]     |
+------------------+      +--------------------+      +--------------------+
```

### 2.1 Radiometric Calibration to $\sigma^0$ (dB)
Digital Numbers (DN) are converted to calibrated radar backscatter intensity in decibels:

$$\sigma^0 (\text{dB}) = 10 \cdot \log_{10}(\text{DN}^2 + \epsilon)$$

### 2.2 Adaptive Lee Despeckling Filter
Multiplicative coherent radar speckle is suppressed while preserving sharp slick boundaries:

$$\hat{I} = \bar{I} + W \cdot (I - \bar{I})$$

$$W = \frac{\sigma_{local}^2}{\sigma_{local}^2 + \sigma_{noise}^2}$$

Where $\bar{I}$ and $\sigma_{local}^2$ are local window mean and variance ($5\times5$ window), and $W \in [0, 1]$ is the adaptive edge-preserving weight.

### 2.3 Dynamic Range Normalization
Marine SAR backscatter typically spans $[-30\text{ dB}, 0\text{ dB}]$. Values are clipped and scaled to $[0.0, 1.0]$, where dark oceanic slicks occupy the lower end of the spectrum.

---

## 3. Deep U-Net Neural Network Architecture

The segmentation model (`ml/models/unet/unet_model.py`) uses an encoder-decoder convolutional architecture with skip connections:

```
Input (1 x 256 x 256)
  |
  v
[DoubleConv: 32] ------------------------ (Skip 1) ---------------------> [Up1 + Conv: 32] -> [Out Conv: 1] -> Sigmoid
  |                                                                             ^
  v (MaxPool 2x2)                                                               |
[DoubleConv: 64] ---------------- (Skip 2) ------------> [Up2 + Conv: 64] -----+
  |                                                           ^
  v (MaxPool 2x2)                                             |
[DoubleConv: 128] ------- (Skip 3) ------> [Up3 + Conv: 128] -+
  |                                            ^
  v (MaxPool 2x2)                              |
[DoubleConv: 256] -----------------------------+ (UpConv 2x2)
```

- **Encoder**: Extracts hierarchical multi-scale context from low-level backscatter gradients to high-level morphological slick shapes.
- **Skip Connections**: Re-introduces high-resolution spatial details to the decoder, ensuring exact boundary localization of oil slick contours.
- **Output**: Single-channel continuous probability map $P(x, y) \in [0.0, 1.0]$.

---

## 4. Training Configuration & Loss Formulation

### 4.1 Combined BCE + Soft Dice Loss
$$\mathcal{L}_{total} = w_{bce} \cdot \mathcal{L}_{BCE} + w_{dice} \cdot \mathcal{L}_{Dice}$$

- **Binary Cross-Entropy**: Penalizes per-pixel classification discrepancies across background and foreground.
- **Soft Dice Loss**: Counteracts extreme class imbalance (oil slicks typically cover $< 3\%$ of a full satellite scene):
  $$\mathcal{L}_{Dice} = 1 - \frac{2 \sum p_i y_i + \epsilon}{\sum p_i + \sum y_i + \epsilon}$$

### 4.2 Hyperparameter Specification (`TrainingConfig`)
| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `base_filters` | `32` | Number of initial convolutional filters |
| `batch_size` | `4` (CPU) / `16` (GPU) | Mini-batch size |
| `learning_rate`| `1e-4` | AdamW initial learning rate |
| `weight_decay` | `1e-4` | L2 weight regularization |
| `lr_scheduler` | `cosine` | Cosine annealing schedule |
| `loss_type` | `bce_dice` ($w=0.5, 0.5$) | Balanced loss function |
| `tile_size` | `256` | Tiling dimensions |
| `val_split` | `0.20` | Validation split ratio |

---

## 5. Seamless Tiled Inference & Probability Heatmaps

### 5.1 Overlapping Sliding-Window Reconstruction
Full satellite swaths are partitioned into tiles with a 25% overlap ($stride=192$, $size=256$). During reconstruction, tile predictions are weighted using a 2D Hann window:

$$w_{hann}(x, y) = \sin^2\left(\frac{\pi x}{N-1}\right) \sin^2\left(\frac{\pi y}{N-1}\right)$$

This eliminates grid edge boundary artifacts and creates a seamless probability map.

### 5.2 RGBA Probability Heatmap
The system generates transparency-masked RGBA overlays:
- Pixels with $P < 0.15$ are 100% transparent.
- Slicks are rendered using the perceptual `TURBO` or `JET` colormap, highlighting high-concentration cores in red and thin peripheral sheens in cyan/blue.

---

## 6. Geospatial Characterization & GeoJSON Pipeline

The raster segmentation mask is converted into vector geospatial features (`app/geospatial/characterization.py`):
1. **Morphological Opening**: $3\times3$ elliptical structuring element removes single-pixel radar noise.
2. **Contour Extraction**: OpenCV vector contour tracing with Douglas-Peucker polygon simplification.
3. **Geodesic Scale Correction**: Computes true ground distances taking into account latitude distortion:
   $$1^\circ \text{Lat} \approx 110.574 \text{ km}, \quad 1^\circ \text{Lon} \approx 111.320 \cdot \cos(\phi) \text{ km}$$
4. **Physical Properties Computed**:
   - True surface area in $km^2$.
   - Geodesic perimeter in $km$.
   - Center of mass centroid $[lon, lat]$.
   - Bounding box $[min\_lon, min\_lat, max\_lon, max\_lat]$.
5. **RFC 7946 GeoJSON Feature Output**: Directly renderable on MapLibre GL, Leaflet, and QGIS.

---

## 7. Empirical Evaluation Framework

Metrics are computed empirically on test sets without fabrication (`ml/evaluation/metrics.py`):

$$\text{IoU} = \frac{TP}{TP + FP + FN}$$

$$\text{Dice / F1} = \frac{2 \cdot TP}{2 \cdot TP + FP + FN}$$

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}$$

Batch evaluation using `ModelEvaluator` exports complete confusion matrix breakdowns:
```json
{
  "mean_metrics": {
    "mean_iou": 0.8124,
    "mean_dice": 0.8965,
    "mean_precision": 0.9102,
    "mean_recall": 0.8831,
    "pixel_accuracy": 0.9912
  }
}
```

---

## 8. Operating Instructions

### Option 1: Execute Training on Custom or Synthetic Datasets
```bash
# From repository root:
python ml/training/train.py
```
Or via FastAPI REST API:
```bash
curl -X POST "http://localhost:8000/api/detection/train?num_epochs=5&batch_size=4"
```

### Option 2: Upload SAR Scene via Web UI or API
```bash
curl -X POST "http://localhost:8000/api/detection/upload-and-detect" \
  -F "file=@/path/to/sentinel1_sar.tif" \
  -F "threshold=0.5" \
  -F "min_area_km2=0.01" \
  -F "min_lon=72.0" \
  -F "min_lat=18.5" \
  -F "max_lon=73.0" \
  -F "max_lat=19.5"
```

### Option 3: Export GeoJSON and Heatmaps
- GeoJSON Feature: `GET /api/detection/{spill_id}/geojson`
- Heatmap PNG: `GET /api/detection/{spill_id}/mask?format_type=heatmap`
- Binary Mask PNG: `GET /api/detection/{spill_id}/mask?format_type=binary`
