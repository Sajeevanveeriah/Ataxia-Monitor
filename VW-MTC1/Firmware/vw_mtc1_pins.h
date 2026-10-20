// VW-MTC1 MazeTrack Controller - Rev B - ESP32-S3-WROOM-1 (N8R2) pin map
// Source of truth: Hardware/KiCad schematic (MCU and MazeIO sheets).
// Rev B touch firmware MUST NOT be flashed onto an unmodified Rev A board.
// Module variant: use N8 / N8R2 (quad PSRAM). Octal-PSRAM variants (R8) reserve GPIO35-37,
// which this board leaves unconnected anyway.
#pragma once

// ---- Hall sensor front end (4 x SS49E in the handle) ----
// Primary path: MCP3204 12-bit ADC on SPI, VREF = +3V3_H (ratiometric with the sensors)
#define PIN_ADC_CS        10   // MCP3204 CS/SHDN (active low)
#define PIN_ADC_MOSI      11   // MCP3204 DIN
#define PIN_ADC_SCK       12   // MCP3204 CLK, run at 1 MHz
#define PIN_ADC_MISO      13   // MCP3204 DOUT
// Backup path: same filtered signals on ESP32-S3 ADC1 (lite build can omit U7)
#define PIN_HALL_F1        4   // ADC1_CH3
#define PIN_HALL_F2        5   // ADC1_CH4
#define PIN_HALL_F3        6   // ADC1_CH5
#define PIN_HALL_F4        7   // ADC1_CH6
#define PIN_HALL_EN_N     16   // LOW = handle sensors + op-amp powered (Q2). Default off (pull-up).

// ---- Handle I2C (I2C1, 2.2k pull-ups to +3V3_H; powered only when HALL_EN_N is LOW) ----
#define PIN_SDA_H         17
#define PIN_SCL_H         18

// ---- On-board I2C (I2C0): OLED (0x3C), ISM330DHCX IMU (0x6A), Qwiic expansion ----
#define PIN_SDA            8
#define PIN_SCL            9
#define PIN_IMU_INT1      15

// ---- Rev B synchronous touch acquisition (ADS8344NB on shared SPI) ----
#define PIN_TOUCH_EXC     41   // 1 kHz hardware carrier, 50% duty
#define PIN_TOUCH_CS      42   // ADS8344NB chip select, active LOW
#define PIN_TOUCH_BUSY    21   // ADS8344NB BUSY, diagnostic input
// CH0 = wire, CH1 = start, CH2 = finish, CH3 = unloaded reference.
// These are analogue measurements; GPIO levels are not contact states.

// ---- microSD (SDMMC 1-bit mode; D1-D3 pulled up) ----
#define PIN_SD_CLK        39
#define PIN_SD_CMD        38
#define PIN_SD_D0         40
#define PIN_SD_CD         14   // LOW = card inserted

// ---- User interface ----
#define PIN_BTN_START      3   // LOW = pressed (10k pull-up)
#define PIN_BTN_MODE       0   // BOOT strap; usable as MODE button after boot
#define PIN_LED_GREEN     47   // forward (active HIGH)
#define PIN_LED_RED       48   // reverse (active HIGH)
#define PIN_LED_AMBER     43   // idle (active HIGH; flickers with U0TXD boot log)
#define PIN_BUZZER        45   // magnetic transducer, drive ~4 kHz PWM (strap pin: keep LOW at boot)
#define PIN_HAPTIC_PWM    46   // ERM motor in handle, 20 kHz PWM (strap pin: pulled LOW)

// ---- Power monitoring ----
#define PIN_VBAT_SENSE     1   // VBAT / 2 (1M/1M + 100 nF). VBAT = 2 * Vadc
#define PIN_VBUS_SENSE     2   // VBUS / 2 when USB present
#define PIN_CHRG_N        44   // LOW = charging (LTC4054 CHRG; enable internal pull-up)

// ---- Native USB (CDC + JTAG) ----
// GPIO19 = USB_D-, GPIO20 = USB_D+
