"""
U-Net Segmentation Architecture for Marine Oil Spill Detection in Sentinel-1 SAR Imagery.
Provides PyTorch implementation with an encoder-decoder backbone, skip connections,
and sigmoid probability output.
"""
import math
from typing import Optional, Dict, Any

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
    class DoubleConv(nn.Module):
        """[Conv2d -> BatchNorm -> ReLU] * 2"""
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.double_conv = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

        def forward(self, x):
            return self.double_conv(x)

    class UNet(nn.Module):
        """
        Classic U-Net architecture for single-channel SAR backscatter inputs.
        Outputs a 1-channel probability map (0 = sea background, 1 = probable oil spill).
        """
        def __init__(self, in_channels: int = 1, out_channels: int = 1, base_filters: int = 32):
            super().__init__()
            self.inc = DoubleConv(in_channels, base_filters)
            self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(base_filters, base_filters * 2))
            self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(base_filters * 2, base_filters * 4))
            self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(base_filters * 4, base_filters * 8))

            self.up1 = nn.ConvTranspose2d(base_filters * 8, base_filters * 4, kernel_size=2, stride=2)
            self.conv1 = DoubleConv(base_filters * 8, base_filters * 4)

            self.up2 = nn.ConvTranspose2d(base_filters * 4, base_filters * 2, kernel_size=2, stride=2)
            self.conv2 = DoubleConv(base_filters * 4, base_filters * 2)

            self.up3 = nn.ConvTranspose2d(base_filters * 2, base_filters, kernel_size=2, stride=2)
            self.conv3 = DoubleConv(base_filters * 2, base_filters)

            self.outc = nn.Conv2d(base_filters, out_channels, kernel_size=1)
            self.sigmoid = nn.Sigmoid()

        def forward(self, x):
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)

            x = self.up1(x4)
            x = torch.cat([x, x3], dim=1)
            x = self.conv1(x)

            x = self.up2(x)
            x = torch.cat([x, x2], dim=1)
            x = self.conv2(x)

            x = self.up3(x)
            x = torch.cat([x, x1], dim=1)
            x = self.conv3(x)

            logits = self.outc(x)
            prob = self.sigmoid(logits)
            return prob
else:
    # Minimal stub class if torch is unavailable
    class UNet:
        def __init__(self, *args, **kwargs):
            pass
