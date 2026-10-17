# Inter-sheet nets for odock-10. Nets listed here get global labels; everything else is local to its sheet.
# Keep names in sync with docs/nets.md. Power symbols are used for POWER_SYMBOL_NETS.

POWER_SYMBOL_NETS = ["GND"]

GLOBAL_NETS = [
    # --- power rails
    "VIN",            # 9-48 V main input rail after OR-ing (PD-in / barrel)
    "VBUS_LAPTOP",    # laptop USB-C VBUS (source up to 28 V x 5 A, or sink 5 V in bus-powered mode)
    "VBUS_PDIN",      # PD-in USB-C VBUS (sink, up to 48 V)
    "VBUS_DS",        # downstream USB-C VBUS (5 V source)
    "VBB_OUT",        # buck-boost output before laptop source switch (5-28 V)
    "VBUS_LSW",       # laptop source switch output, upstream of the 5 mOhm shunt (PMG1 port-0 CSA +)
    "+5V", "+3V3", "+1V15", "+1V1",
    "PMG1_VDDD",      # PMG1 internal supply (from +3V3 or laptop VBUS) - exists in a dead deck
    "+5V_USBA1", "+5V_USBA2",
    # --- power-path control / status
    "EXT_PWR_PRESENT",  # high when PD-in or barrel supplies VIN
    "PDIN_PRESENT",     # high when PD-in contract is active (informational; no hardware priority)
    "VBB_PG",           # buck-boost power good
    "VBB_EN",           # buck-boost enable (PMG1)
    "VBB_VSEL0", "VBB_VSEL1", "VBB_VSEL2",  # buck-boost voltage select (PMG1 GPIO only)
    "LAPTOP_SRC_EN",    # PMG1 request to enable source switch to laptop (gated in hardware)
    "LAPTOP_SNK_EN",    # enable bus-power sink switch (laptop VBUS -> +5V), only without ext power
    "LAPTOP_OVP_N",     # hardware OVP trip (active low)
    # --- I2C / SMBus
    "I2C_PD_SCL", "I2C_PD_SDA",     # RP2350 <-> PMG1 (host interface), TPS26750
    "I2C_SYS_SCL", "I2C_SYS_SDA",   # RP2350 <-> sensors, INA2xx, EEPROMs
    "I2C_PD_INT_N", "PDIN_INT_N",
    "HUB_SMB_CLK", "HUB_SMB_DAT", "HUB_SMB_PU", "HUB_RESET_N",
    # --- USB 2.0 / 3.x links between sheets
    "LAPTOP_USB_DP", "LAPTOP_USB_DN",          # laptop USB2 to hub upstream
    "HUB_UP_SS_TXP", "HUB_UP_SS_TXN", "HUB_UP_SS_RXP", "HUB_UP_SS_RXN",
    "DP_ML0_P", "DP_ML0_N", "DP_ML1_P", "DP_ML1_N", "DP_AUX_P", "DP_AUX_N", "DP_HPD",
    # --- PMG1 debug / control from RP2350
    "PMG1_SWDIO", "PMG1_SWCLK", "PMG1_XRES_N",
    # --- power-good from rails
    "PG_5V",           # LM5148 5 V buck power-good (power_rails) -> laptop sink hand-over gating
    "RAILS_PG",        # open-drain, +1V15 good (power_rails) -> wire-OR into HUB_RESET_N
    # --- USB-C ports <-> PD controller (usbc_muxes <-> pd_pmg1)
    "LAPTOP_CC1", "LAPTOP_CC2", "DS_CC1", "DS_CC2",
    "MUX_UP_CTL0", "MUX_UP_CTL1", "MUX_UP_FLIP",     # TUSB1064 (laptop side) control from PMG1 port 0
    "MUX_DS_CTL0", "MUX_DS_CTL1", "MUX_DS_FLIP",     # TUSB1046 (downstream side) control from PMG1 port 1
    "UP_HPD", "DS_HPD",                               # HPD to/from muxes (see pd_pmg1 design notes)
    # --- hub links. SS pairs named from the HUB's point of view (TX = hub transmits).
    "HUB_DSC_SS_TXP", "HUB_DSC_SS_TXN", "HUB_DSC_SS_RXP", "HUB_DSC_SS_RXN", "HUB_DSC_DP", "HUB_DSC_DN",  # -> TUSB1046
    "USBA1_SS_TXP", "USBA1_SS_TXN", "USBA1_SS_RXP", "USBA1_SS_RXN", "USBA1_DP", "USBA1_DN",
    "USBA2_SS_TXP", "USBA2_SS_TXN", "USBA2_SS_RXP", "USBA2_SS_RXN", "USBA2_DP", "USBA2_DN",
    "CR_SS_TXP", "CR_SS_TXN", "CR_SS_RXP", "CR_SS_RXN", "CR_DP", "CR_DN",          # GL3224 card reader
    "ETH_SS_TXP", "ETH_SS_TXN", "ETH_SS_RXP", "ETH_SS_RXN", "ETH_DP", "ETH_DN",    # RTL8156BG
    "MCU_USB_DP", "MCU_USB_DN",                                                     # RP2350 (USB2-only hub port)
    "USBA1_PWR_EN", "USBA2_PWR_EN", "USBA1_OCS_N", "USBA2_OCS_N",                  # hub port power / overcurrent
    # --- MCU <-> display & UI (mcu <-> display_ui)
    "LCD_SCK", "LCD_MOSI", "LCD_CS_N", "LCD_DC", "LCD_RST_N", "LCD_BL_PWM",
    "BTN_A_N", "BTN_B_N",                     # user buttons (active low)
    "I2C_EXT_SCL", "I2C_EXT_SDA",             # Qwiic / user I2C (separate from I2C_SYS)
    "HDR_GPIO0", "HDR_GPIO1", "HDR_GPIO2", "HDR_GPIO3", "HDR_GPIO4", "HDR_GPIO5",
    "HDR_GPIO6", "HDR_GPIO7", "HDR_ADC0", "HDR_ADC1",   # user header (RP2350B spare pins)
    # --- MCU <-> ethernet / card reader / sensors
    "ETH_LED0", "ETH_LED1", "ETH_LED2",       # RTL8156BG LED pins (link speed / activity) -> MCU inputs
    "ETH_RESET_N",
    "ETH_I2C_EN",                             # TCA9534 P6 -> enables PHY I2C bridge for one-time MAC eFuse write
    "CR_CD_SD_N", "CR_CD_USD_N", "CR_LED",    # card detect + activity from card reader / sockets
    "TEMP_ALERT_N",                           # TMP1075 ALERT wired-OR (open drain)
    "NTC_ADC0", "NTC_ADC1",                   # hot-spot NTCs -> RP2350 ADC
    # --- misc control
    "USBA1_FORCE_EN", "USBA2_FORCE_EN", "USBA1_ISENSE", "USBA2_ISENSE",
]
