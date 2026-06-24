<div align="center">

<img src="docs/assets/seaforged_logo.png" alt="Seaforged Drone Technologies" width="600"/>

# Seaforged mLRS LR2021

**Dual-Band LoRa Radio Link for FPV Drones and Autonomous Systems**

[![Firmware](https://img.shields.io/badge/mLRS-Compiles%20Clean-brightgreen)](firmware/)
[![ELRS](https://img.shields.io/badge/ELRS%203.x-Compiles%20Clean-brightgreen)](firmware/elrs-lr2021-driver/)
[![Hardware](https://img.shields.io/badge/Hardware-Link%20Proven-brightgreen)](firmware/tests/)
[![NDAA](https://img.shields.io/badge/Supply%20Chain-NDAA%20Compliant-blue)](docs/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

*Semtech LR2021 · STM32G491RET6 · SKY65383-11 FEM · Single-chip dual-band*

</div>

---

## What This Is

The Seaforged mLRS LR2021 is a single-PCB, dual-band (915 MHz + 2.4 GHz) LoRa radio link built on Semtech's Gen 4 LR2021 transceiver. It runs two firmware targets from one board — **mLRS** for MAVLink-oriented autonomous systems and **ExpressLRS** for high-performance FPV RC links.

The key differentiator is **intelligent band failover**: a composite Link Health Score (LHS) algorithm monitors SNR, RSSI, and link quality in real time and switches bands automatically when interference or range conditions degrade — without pilot intervention, without dropped packets, without a second chip.

**100% NDAA-compliant supply chain.** No Chinese-manufactured ICs anywhere in the BOM.

---

## Hardware

| Component | Part | Role |
|---|---|---|
| Transceiver | Semtech LR2021 (QFN-32) | Gen 4 LoRa, 915 MHz + 2.4 GHz, single chip |
| MCU | STMicroelectronics STM32G491RET6 | Cortex-M4F, 170 MHz, 512KB flash |
| FEM | Skyworks SKY65383-11 | Sub-GHz PA/LNA front-end module |
| Crystal | Rakon FTR5238-A0 | 32 MHz TCXO reference |
| Power | TI TPS62160 + MIC5219 | Buck + LDO regulated 3.45V rail |

**Dev hardware (proven working):**
- 2× NUCLEO-G491RE evaluation boards
- 2× Seeed Studio Wio-LR2021 EVK (e758v03a expansion boards)

---

## Firmware Status

### mLRS Target

| Milestone | Status |
|---|---|
| SPI GetVersion — chip ID confirmed | ✅ HW=0x21 |
| Dual-band TX/RX link (915 MHz) | ✅ RSSI -20 dBm, SNR 15, 4500+ packets |
| `Lr2021Interface` mLRS adapter | ✅ Hardware proven |
| TX target compiles against upstream mLRS | ✅ Zero errors, 29KB |
| RX target compiles against upstream mLRS | ✅ Zero errors, 11KB |
| LHS failover algorithm | ✅ 18 unit tests pass |
| Automated CI smoke test | ✅ `dual_link_smoke.py` |

### ELRS Target

| Milestone | Status |
|---|---|
| LR2021 driver port from LR1121 | ✅ Complete |
| ELRS 3.x.x-maintenance integration | ✅ Zero compile errors |
| STM32G491RE PlatformIO target | ✅ `DIY_900_LR2021_STM32G491RE` |
| Hardware bind test | 🔲 Pending hardware validation |

---

## Novel Features

### Link Health Score (LHS) Failover

The LHS algorithm computes a composite signal quality metric every packet cycle:

```
LHS = (SNR × 0.45) + (RSSI × 0.30) + (LQ × 0.25)
```

- **EMA smoothing** filters packet-to-packet noise
- **Asymmetric hysteresis** — fails at LHS < 50, recovers at LHS > 70 — prevents oscillation
- **Temporal confirmation** — 3 consecutive failures trigger a switch, 5 consecutive recoveries restore the band
- **Pre-negotiated switching** — TX embeds "SWITCH at packet N+5" in consecutive packets, eliminating dead time

Band switch time: **< 140 µs** with CalibFE caching. No pilot action required.

### Single-Chip Dual-Band

The LR2021 handles both 915 MHz and 2.4 GHz from one transceiver using internal PA selection (`SelPa`) and automatic FEM routing via `SetDioRfSwitchConfig`. Upstream mLRS achieves dual-band with two separate chips. Seaforged does it with one.

---

## Repository Structure

```
Seaforged-mLRS/
├── README.md
├── firmware/
│   ├── Common/
│   │   ├── hal/lr2021/          # Silicon-verified LR2021 SPI driver
│   │   │   ├── lr2021_driver.h  # All opcodes (20/20 silicon-tested)
│   │   │   ├── lr2021_driver.cpp
│   │   │   ├── lr2021_interface.h   # mLRS radio abstraction layer
│   │   │   └── lr2021_interface.cpp
│   │   └── lhs/                 # LHS failover algorithm
│   │       ├── failover_lhs.h
│   │       └── failover_lhs.cpp
│   ├── elrs-lr2021-driver/      # ELRS 3.x LR2021 driver
│   │   ├── LR2021_Regs.h        # All LR2021 opcodes remapped from LR1121
│   │   ├── LR2021.h/.cpp        # Driver: TX, RX, IRQ, power, FIFO
│   │   ├── LR2021_hal.h/.cpp    # SPI HAL with Direct FIFO protocol
│   │   └── LR2021Driver.h       # Convenience include
│   ├── targets/
│   │   ├── tx-seaforged-lr2021-g491re/  # mLRS TX target
│   │   └── rx-seaforged-lr2021-g491re/  # mLRS RX target
│   └── tests/
│       ├── dual_link_smoke.py   # Automated TX/RX link validation
│       ├── mlrs_interface_link/ # mLRS interface hardware test
│       └── dual_link_tx/rx/     # Standalone link test firmware
├── hardware/
│   ├── kicad/                   # Schematic and PCB design files
│   └── gerbers/                 # PCB fabrication files (Sierra Circuits)
├── docs/
│   ├── assets/
│   │   └── seaforged_logo.png
│   └── references/              # Recon reports, audit results, datasheets
└── tools/
    └── lr1121_port_auditor.py   # Scans code for LR1121→LR2021 porting errors
```

---

## Build Instructions

### Prerequisites

- STM32CubeIDE 2.1.1+
- Python 3.11+
- PlatformIO Core 6.x
- arm-none-eabi-gcc 14.x
- Two NUCLEO-G491RE boards
- Two Seeed Studio Wio-LR2021 EVK boards

### mLRS Target (STM32CubeIDE)

```bash
# 1. Clone upstream mLRS
git clone https://github.com/olliw42/mLRS.git C:/Projects/mLRS-upstream

# 2. Clone this repo into the mLRS workspace
git clone https://github.com/Seaforged/Seaforged-mLRS.git

# 3. Open STM32CubeIDE, import project:
#    File → Import → Existing Projects → C:/Projects/mLRS-upstream/mLRS/
#    Select: tx-seaforged-lr2021-g491re

# 4. Headless build (or use CubeIDE GUI)
"C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/stm32cubeidec.exe" \
  --launcher.suppressErrors -nosplash \
  -application org.eclipse.cdt.managedbuilder.core.headlessbuild \
  -data C:/Projects/mLRS-upstream/mLRS-workspace \
  -build tx-seaforged-lr2021-g491re/Release

# 5. Flash Board 1 (TX) — ST-Link SN: 0019002A3235510837333439
```

### ELRS Target (PlatformIO)

```bash
# 1. Clone ELRS 3.x maintenance branch
git clone --branch 3.x.x-maintenance \
  https://github.com/ExpressLRS/ExpressLRS.git \
  C:/Projects/ExpressLRS-3x

# 2. Copy LR2021 driver into ELRS
xcopy firmware\elrs-lr2021-driver\ \
      C:\Projects\ExpressLRS-3x\src\lib\LR2021Driver\ /E /I

# 3. Build TX target
cd C:/Projects/ExpressLRS-3x/src
pio run -e DIY_900_LR2021_STM32G491RE
```

### Run Smoke Test

```bash
cd C:/Projects/MLRS
python firmware/tests/dual_link_smoke.py --duration 12 --min-packets 5
# Expected: PASS — packets flowing, counter span ≥ 5, RSSI ~-20 dBm, SNR 14-15
```

---

## Wiring (Dev Board Setup)

```
Wio-LR2021 EVK (Xiao Socket)    →    NUCLEO-G491RE
─────────────────────────────────────────────────────
D10  (NSS)      →  PB6   (CN10-13)
D8   (SCK)      →  PA5   (CN7-10)
D9   (MISO)     →  PA6   (CN7-12)
D7   (MOSI)     →  PA7   (CN7-14)
D2   (NRESET)   →  PA10  (CN10-33)
D1   (BUSY)     →  PB4   (CN10-27)
3V3             →  3.3V  (CN6-4)
GND             →  GND   (CN6-6)
```

> ⚠️ **3.3V ONLY.** The LR2021 will be damaged by 5V. No level shifter needed — both sides are 3.3V logic.

> ⚠️ **Use Xiao pin numbering**, not Arduino pin numbering. D8/D9/D10 on the Xiao socket ≠ D11/D12/D13 on the Arduino header.

---

## NDAA Compliance

Every component in the Seaforged BOM is sourced from allied nations with no Chinese-manufactured ICs:

| Component | Manufacturer | Country |
|---|---|---|
| LR2021 transceiver | Semtech | 🇺🇸 United States |
| STM32G491RET6 MCU | STMicroelectronics | 🇨🇭🇫🇷🇮🇹 Switzerland/France/Italy |
| SKY65383-11 FEM | Skyworks Solutions | 🇺🇸 United States |
| Crystal | Rakon | 🇳🇿 New Zealand |
| Passives | Vishay, Murata | 🇺🇸🇯🇵 USA/Japan |

This makes the Seaforged LR2021 compatible with Blue UAS Framework submission and DoD procurement requirements that restrict FCC Covered List components.

---

## Development Roadmap

### V1 — Hardware Proven ✅
- [x] Silicon validation (S6)
- [x] Dual-band LoRa link (S7)
- [x] mLRS upstream integration (S8)
- [x] ELRS LR2021 driver (S9)

### V2 — Custom PCB (In Progress)
- [ ] KiCad schematic — all phases (2A power ✅, 2B-2E in progress)
- [ ] PCB layout (Quilter.ai + manual RF section)
- [ ] Sierra Circuits fabrication (Rev A)
- [ ] Hardware bringup on custom PCB
- [ ] FCC Part 15 pre-compliance scan

### V3 — Product Launch
- [ ] AES-128 encryption + PSK binding
- [ ] Secure boot (RDP Level 2)
- [ ] Blue UAS Framework submission
- [ ] FCC Part 15 certification

---

## Key Technical References

- **LR2021 Datasheet** — Rev 1.1, Oct 2025 (Semtech)
- **AN1200.104** — LR2021 Modem Interface (SPI protocol, FIFO access)
- **AN1200.102** — LR2021 LoRa Performance (sensitivity, range)
- **AN1200.107** — LR2021 Analog Improvements (PA config)
- **NUCLEO-G491RE** — MB1367 Rev C schematic

---

## Tools

### LR1121 Port Auditor

Scans any C/C++/Python codebase for LR1121 opcodes that are wrong on LR2021:

```bash
# Audit a driver directory
python tools/lr1121_port_auditor.py --path firmware/ --report

# Audit ELRS LR1121 driver before porting
python tools/lr1121_port_auditor.py \
  --path C:/Projects/ExpressLRS-3x/src/lib/LR1121Driver/ --report
```

Flags: wrong opcodes, 6-byte PacketParams (should be 4), BW500=0x09 (should be 0x06), missing SetRxPath, DIO1 references (doesn't exist on LR2021), wrong IRQ bit positions.

---

## About Seaforged

Seaforged Drone Technologies is building NDAA-compliant radio link hardware for FPV drones and autonomous systems. The Seaforged LR2021 targets both the civilian FPV market (ELRS firmware, sub-$150/pair) and defense/government applications (mLRS firmware, dual-FEM variant, Blue UAS documentation).

**Contact:** seaforged.io  
**Founder:** Nicholas Dale Wooten

---

<div align="center">

<img src="docs/assets/seaforged_logo.png" alt="Seaforged Drone Technologies" width="400"/>

*Built in the USA. Forged for the field.*

</div>
