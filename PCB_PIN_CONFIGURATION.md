# PCB-Friendly Pin Configuration Guide

This guide provides several pin configuration options optimized for PCB design and routing.

## 🎯 **Recommended: Option 1 - Pure SPI Configuration**

### **Pin Assignment:**
```
ESP32 Pin    Display Pin    Function
---------    -----------    --------
GPIO 23      MOSI          SPI Data Out
GPIO 18      SCLK          SPI Clock
GPIO 5       CS            Chip Select
GPIO 17      DC            Data/Command
GPIO 16      RST           Reset
GPIO 2       BL            Backlight (optional)
```

### **PCB Benefits:**
- ✅ All pins grouped together (GPIO 2, 5, 16, 17, 18, 23)
- ✅ Uses standard SPI interface
- ✅ Easy to route on PCB
- ✅ No I2C conflicts
- ✅ Backlight control included

---

## 🔄 **Alternative: Option 2 - Compact SPI Grouping**

### **Pin Assignment:**
```
ESP32 Pin    Display Pin    Function
---------    -----------    --------
GPIO 13      MOSI          SPI Data Out
GPIO 14      SCLK          SPI Clock
GPIO 15      CS            Chip Select
GPIO 4       DC            Data/Command
GPIO 0       RST           Reset
GPIO 2       BL            Backlight (optional)
```

### **PCB Benefits:**
- ✅ Very compact grouping (GPIO 0, 2, 4, 13, 14, 15)
- ✅ All pins on one side of ESP32
- ✅ Minimal trace length
- ✅ Easy to route in tight spaces

---

## 🔄 **Alternative: Option 3 - Mixed Interface (I2C + SPI)**

### **Pin Assignment:**
```
ESP32 Pin    Display Pin    Function
---------    -----------    --------
GPIO 21      SDA           I2C Data
GPIO 22      SCL           I2C Clock
GPIO 5       CS            SPI Chip Select
GPIO 17      DC            Data/Command
GPIO 16      RST           Reset
GPIO 2       BL            Backlight (optional)
```

### **PCB Benefits:**
- ✅ Uses I2C for data (simpler protocol)
- ✅ Only 3 additional pins needed
- ✅ Good for displays that support I2C mode

---

## 🔄 **Alternative: Option 4 - Parallel Interface (Fastest)**

### **Pin Assignment:**
```
ESP32 Pin    Display Pin    Function
---------    -----------    --------
GPIO 19      D0            Data Bit 0
GPIO 18      D1            Data Bit 1
GPIO 5       D2            Data Bit 2
GPIO 17      D3            Data Bit 3
GPIO 16      D4            Data Bit 4
GPIO 4       D5            Data Bit 5
GPIO 0       D6            Data Bit 6
GPIO 2       D7            Data Bit 7
GPIO 15      CS            Chip Select
GPIO 14      DC            Data/Command
GPIO 13      RST           Reset
GPIO 12      BL            Backlight (optional)
```

### **PCB Benefits:**
- ✅ Fastest data transfer
- ✅ All pins grouped together
- ✅ Good for high-resolution displays
- ✅ More pins but better performance

---

## 🔧 **How to Change Pin Configuration**

### **Method 1: Edit config.h**
```cpp
// In include/config.h, uncomment the desired configuration:

// Option 1: Pure SPI (Recommended)
#define DISPLAY_MOSI 23
#define DISPLAY_SCLK 18
#define DISPLAY_CS   5
#define DISPLAY_DC   17
#define DISPLAY_RST  16
#define DISPLAY_BL   2

// Option 2: Compact SPI
// #define DISPLAY_MOSI 13
// #define DISPLAY_SCLK 14
// #define DISPLAY_CS   15
// #define DISPLAY_DC   4
// #define DISPLAY_RST  0
// #define DISPLAY_BL   2

// Option 3: I2C + SPI
// #define DISPLAY_SDA 21
// #define DISPLAY_SCL 22
// #define DISPLAY_CS   5
// #define DISPLAY_DC   17
// #define DISPLAY_RST  16
// #define DISPLAY_BL   2
```

### **Method 2: PlatformIO Build Flags**
```ini
; In platformio.ini, add pin definitions:
build_flags = 
    -DDISPLAY_MOSI=23
    -DDISPLAY_SCLK=18
    -DDISPLAY_CS=5
    -DDISPLAY_DC=17
    -DDISPLAY_RST=16
    -DDISPLAY_BL=2
```

---

## 📋 **PCB Design Recommendations**

### **1. Pin Grouping**
- Group all display pins together on one side of the ESP32
- Use the same side for power and ground pins
- Keep signal traces as short as possible

### **2. Trace Routing**
- Use 0.2mm trace width for signal lines
- Use 0.5mm trace width for power lines
- Keep traces parallel and evenly spaced
- Add ground planes between signal layers

### **3. Connector Placement**
- Place display connector near the grouped pins
- Use a standard connector (JST, Molex, or header)
- Consider using a flex cable for the display connection

### **4. Power Considerations**
- Add decoupling capacitors near the ESP32
- Use separate power traces for display backlight
- Consider adding a power switch for the backlight

---

## 🔍 **Pin Conflict Check**

### **ESP32 Pin Usage:**
```
Pin    Function                    Available for Display
---    --------                    --------------------
0      Boot/Reset                  ✅ (if not using boot button)
1      TX (Serial)                 ❌ (used for debugging)
2      Built-in LED               ✅ (can be used for backlight)
3      RX (Serial)                 ❌ (used for debugging)
4      GPIO                       ✅
5      GPIO                       ✅
12     GPIO                       ✅
13     GPIO                       ✅
14     GPIO                       ✅
15     GPIO                       ✅
16     GPIO                       ✅
17     GPIO                       ✅
18     GPIO                       ✅
19     GPIO                       ✅
21     GPIO                       ✅
22     GPIO                       ✅
23     GPIO                       ✅
```

### **Recommended Pin Selection:**
- **Avoid**: GPIO 1, 3 (Serial), GPIO 6-11 (Flash), GPIO 24-39 (Input only)
- **Prefer**: GPIO 2, 4, 5, 12-19, 21-23 (GPIO pins)
- **Group**: Select pins that are physically close together

---

## 🚀 **Quick Start for PCB Design**

1. **Choose Option 1** (Pure SPI) for easiest routing
2. **Place ESP32** in center of PCB
3. **Group display pins** on one side (GPIO 2, 5, 16, 17, 18, 23)
4. **Add connector** near the grouped pins
5. **Route traces** directly from ESP32 to connector
6. **Add power** and ground planes
7. **Test** with breadboard first before PCB fabrication

This configuration will make your PCB much easier to design and route!
