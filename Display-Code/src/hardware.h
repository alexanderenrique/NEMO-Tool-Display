/*
 * NEMO Tool Display - Hardware configuration
 * Single source of truth for TFT and pins. Track this file between workspaces.
 * TFT_eSPI uses this when USER_SETUP_LOADED is defined (via platformio.ini -include).
 */

#ifndef HARDWARE_H
#define HARDWARE_H

/* Tell TFT_eSPI to use our defines instead of User_Setup.h */
#define USER_SETUP_LOADED
#define USER_SETUP_INFO "hardware.h"

/* -----------------------------------------------------------------------------
 * Display driver (only one uncommented)
 * ILI9341 = 240x320 typical; ILI9488 = 480x320 typical
 * ----------------------------------------------------------------------------- */
// #define ILI9341_DRIVER
#define ILI9488_DRIVER

/* -----------------------------------------------------------------------------
 * ESP32 SPI pins (from README pinout)
 * Display: SCK=25, MOSI=26, DC/RS=27, RESET=14, CS=13
 * Touch:   T_DO (MISO)=32, T_DIN (MOSI)=26, T_CS=33, T_CLK=25, T_IRQ not specified
 * ----------------------------------------------------------------------------- */

 //T_IRQ not used
 #define TFT_MISO 32   // T_DO
 //T_DIN = 26, TFT_MOSI = 26
#define TOUCH_CS  33  // T_CS
//T_CLK = 25
//TFT_MISO = 32
//LED
#define TFT_SCLK 25
#define TFT_MOSI 26   // T_DIN
#define TFT_DC    27  /* Data/Command (DC/RS) */
#define TFT_RST   14  /* Reset */
#define TFT_CS    13  /* Chip select */
//GND
//VCC

#define SPI_TOUCH_FREQUENCY  2500000  /* XPT2046 max ~2.5MHz; required for touch */

/* XPT2046 calibration (480x320) - adjust if touch is off; use TFT_eSPI Touch_calibrate sketch to find values */
#define XPT2046_X_MIN     200
#define XPT2046_X_MAX     3800
#define XPT2046_Y_MIN     200
#define XPT2046_Y_MAX     3800

/* SPI transactions required for ESP32 to switch between TFT and touch on shared bus */
#define SUPPORT_TRANSACTIONS

/* -----------------------------------------------------------------------------
 * SPI frequency (Hz)
 * ----------------------------------------------------------------------------- */
#define SPI_FREQUENCY       27000000
#define SPI_READ_FREQUENCY  16000000

/* -----------------------------------------------------------------------------
 * Fonts to load (comment out to save flash)
 * ----------------------------------------------------------------------------- */
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SMOOTH_FONT

#endif /* HARDWARE_H */
