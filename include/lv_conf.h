/*
 * LVGL Configuration for NEMO Tool Display
 * Basic configuration for ESP32 with TFT display
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#define LV_USE_LOG 1
#if LV_USE_LOG
    #define LV_LOG_LEVEL LV_LOG_LEVEL_INFO
    #define LV_LOG_PRINTF 1
#endif

/* Color depth */
#define LV_COLOR_DEPTH 16

/* Memory settings */
#define LV_MEM_SIZE (32U * 1024U)          /*[bytes]*/
#define LV_MEM_ADR 0                       /*[0x0000-0xFFFF]*/
#define LV_MEM_AUTO_DEFRAG 1

/* Display buffer size */
#define LV_DISP_DEF_REFR_PERIOD 30
#define LV_INDEV_DEF_READ_PERIOD 30

/* Display dimensions */
#define LV_HOR_RES_MAX 480
#define LV_VER_RES_MAX 320

/* Input device settings */
#define LV_INDEV_DEF_DRAG_LIMIT 10
#define LV_INDEV_DEF_DRAG_THROW 10
#define LV_INDEV_DEF_LONG_PRESS_TIME 400
#define LV_INDEV_DEF_LONG_PRESS_REP_TIME 100
#define LV_INDEV_DEF_GESTURE_LIMIT 50
#define LV_INDEV_DEF_GESTURE_MIN_VELOCITY 3

/* Feature usage - Only include features actually used */
#define LV_USE_ANIMATION 0  // Not used in simple display
#define LV_USE_EXTRA 0      // Disable all extra features
#define LV_USE_LAYOUTS 0    // Disable layouts
#define LV_USE_LOGS 0       // Disable logs
#define LV_USE_MEM_MONITOR 0 // Disable memory monitor
#define LV_USE_MSG 0        // Disable message system
#define LV_USE_SNAPSHOT 0   // Disable snapshot

/* Text settings */
#define LV_TXT_ENC LV_TXT_ENC_UTF8
#define LV_TXT_BREAK_CHARS " ,.;:-_"
#define LV_TXT_LINE_BREAK_LONG_LEN 0
#define LV_TXT_LINE_BREAK_LONG_PRE_MIN_LEN 3
#define LV_TXT_LINE_BREAK_LONG_POST_MIN_LEN 3

/* Widget usage - Only include widgets actually used */
#define LV_USE_BAR 0      // Progress bar - not used
#define LV_USE_BTN 0      // Button - not used
#define LV_USE_LABEL 1    // All text labels - USED
#define LV_USE_ARC 0      // Arc - not used
#define LV_USE_BTNMATRIX 0 // Button matrix - not used
#define LV_USE_CANVAS 0   // Canvas - not used
#define LV_USE_CHECKBOX 0 // Checkbox - not used
#define LV_USE_DROPDOWN 0 // Dropdown - not used
#define LV_USE_IMG 0      // Image - not used
#define LV_USE_LINE 0     // Line - not used
#define LV_USE_ROLLER 0   // Roller - not used
#define LV_USE_SLIDER 0   // Slider - not used
#define LV_USE_SWITCH 0   // Switch - not used
#define LV_USE_TABLE 0    // Table - not used
#define LV_USE_TEXTAREA 0 // Text area - not used

/* Extra widgets - Disable all extra widgets to avoid dependencies */
#define LV_USE_ANIMIMG 0
#define LV_USE_CALENDAR 0
#define LV_USE_CHART 0
#define LV_USE_COLORWHEEL 0
#define LV_USE_IMGBTN 0
#define LV_USE_KEYBOARD 0
#define LV_USE_LED 0
#define LV_USE_LIST 0
#define LV_USE_MENU 0
#define LV_USE_METER 0
#define LV_USE_MSGBOX 0
#define LV_USE_SPAN 0
#define LV_USE_SPINBOX 0
#define LV_USE_SPINNER 0
#define LV_USE_TABVIEW 0
#define LV_USE_TILEVIEW 0
#define LV_USE_WIN 0

/* Themes - Only use default theme */
#define LV_USE_THEME_DEFAULT 1
#define LV_USE_THEME_BASIC 0
#define LV_USE_THEME_MONO 0

/* Font usage - Only include fonts actually used */
#define LV_FONT_MONTSERRAT_8  0
#define LV_FONT_MONTSERRAT_10 0
#define LV_FONT_MONTSERRAT_12 0
#define LV_FONT_MONTSERRAT_14 1  // Default font
#define LV_FONT_MONTSERRAT_16 1  // Medium text
#define LV_FONT_MONTSERRAT_18 1  // Status text
#define LV_FONT_MONTSERRAT_20 0
#define LV_FONT_MONTSERRAT_22 0
#define LV_FONT_MONTSERRAT_24 1  // Tool name
#define LV_FONT_MONTSERRAT_26 0
#define LV_FONT_MONTSERRAT_28 0
#define LV_FONT_MONTSERRAT_30 0
#define LV_FONT_MONTSERRAT_32 0
#define LV_FONT_MONTSERRAT_34 0
#define LV_FONT_MONTSERRAT_36 0
#define LV_FONT_MONTSERRAT_38 0
#define LV_FONT_MONTSERRAT_40 0
#define LV_FONT_MONTSERRAT_42 0
#define LV_FONT_MONTSERRAT_44 0
#define LV_FONT_MONTSERRAT_46 0
#define LV_FONT_MONTSERRAT_48 0

/* Disable unused fonts */
#define LV_FONT_DEJAVU_16_PERSIAN_HEBREW 0
#define LV_FONT_SIMSUN_16_CJK 0
#define LV_FONT_UNSCII_8 0
#define LV_FONT_UNSCII_16 0

/* File system - Disabled for simple display */
#define LV_USE_FS_STDIO 0
#define LV_USE_FILESYSTEM 0

/* Extra libraries - Disable all */
#define LV_USE_BMP 0
#define LV_USE_FFMPEG 0
#define LV_USE_FREETYPE 0
#define LV_USE_FS_FATFS 0
#define LV_USE_FS_LITTLEFS 0
#define LV_USE_FS_POSIX 0
#define LV_USE_FS_STDIO 0
#define LV_USE_FS_WIN32 0
#define LV_USE_GIF 0
#define LV_USE_PNG 0
#define LV_USE_QRCODE 0
#define LV_USE_RLOTTIE 0
#define LV_USE_SJPG 0
#define LV_USE_TINY_TTF 0

/* Others - Only enable what we need */
#define LV_USE_USER_DATA 0
#define LV_USE_PERF_MONITOR 0
#define LV_USE_API_EXTENSION_V6 0

#endif /*LV_CONF_H*/
