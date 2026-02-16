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
 * ESP32 SPI pins
 * ----------------------------------------------------------------------------- */
#define TFT_MISO 19   /* Leave disconnected if no other SPI devices share MISO */
#define TFT_MOSI 23
#define TFT_SCLK 18
#define TFT_CS    15  /* Chip select */
#define TFT_DC    2   /* Data/Command */
#define TFT_RST   4   /* Reset (use -1 if tied to board RST) */
/* #define TFT_BL   32 */
/* #define TFT_BACKLIGHT_ON  HIGH */

/* -----------------------------------------------------------------------------
 * SPI frequency (Hz)
 * ----------------------------------------------------------------------------- */
#define SPI_FREQUENCY       27000000
#define SPI_READ_FREQUENCY  16000000
#define SPI_TOUCH_FREQUENCY 2500000

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
