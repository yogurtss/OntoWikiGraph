# LPDDR5X Memory Example

The LPDDR5X device supports a peak data rate of 8533 MT/s on each 16-bit channel.
In the tested configuration, tRCD and tRP are both 18 ns at VDD2H = 1.05 V.
Relative to LPDDR5, LPDDR5X increases bandwidth but raises PHY power.
The die is fabricated on a 12 nm process.

## HBM3 Stack

The HBM3 stack contains 8 DRAM dies and is interconnected with a base die through TSVs.
At a 6.4 Gb/s per-pin rate, the stack bandwidth reaches 819 GB/s.
The controller uses ECC to improve reliability.

