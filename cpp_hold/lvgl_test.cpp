/*
 * LVGL Test Script for NEMO Tool Display
 * Simple test to verify LVGL functionality on ESP32 with TFT display
 */

#include <lvgl.h>
#include <TFT_eSPI.h>
#include <SPI.h>

// Display configuration
TFT_eSPI tft = TFT_eSPI();

// LVGL display buffer
static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[480 * 10]; // 10 lines buffer

// Display driver
static lv_disp_drv_t disp_drv;

// Function declarations
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void setup_lvgl();
void create_test_ui();

void setup() {
  Serial.begin(9600);
  Serial.println("LVGL Test Starting...");
  
  // Initialize TFT display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  
  // Initialize LVGL
  lv_init();
  
  // Initialize display buffer
  lv_disp_draw_buf_init(&draw_buf, buf, NULL, 480 * 10);
  
  // Initialize display driver
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = 480;
  disp_drv.ver_res = 320;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);
  
  // Create test UI
  create_test_ui();
  
  Serial.println("LVGL Test Ready!");
}

void loop() {
  lv_timer_handler(); // Handle LVGL tasks
  delay(5);
}

void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
  uint32_t w = (area->x2 - area->x1 + 1);
  uint32_t h = (area->y2 - area->y1 + 1);
  
  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.pushColors((uint16_t*)&color_p->full, w * h, true);
  tft.endWrite();
  
  lv_disp_flush_ready(disp);
}

void create_test_ui() {
  // Create a simple container
  lv_obj_t *cont = lv_obj_create(lv_scr_act());
  lv_obj_set_size(cont, 460, 300);
  lv_obj_center(cont);
  lv_obj_set_style_bg_color(cont, lv_color_hex(0x2C2C2C), 0);
  lv_obj_set_style_border_width(cont, 2, 0);
  lv_obj_set_style_border_color(cont, lv_color_hex(0x00AAFF), 0);
  
  // Add title label
  lv_obj_t *title = lv_label_create(cont);
  lv_label_set_text(title, "LVGL Test");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_30, 0);
  lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);
  
  // Add status label
  lv_obj_t *status = lv_label_create(cont);
  lv_label_set_text(status, "Display: OK\nTouch: N/A\nMemory: OK");
  lv_obj_set_style_text_color(status, lv_color_hex(0x00FF00), 0);
  lv_obj_align(status, LV_ALIGN_CENTER, 0, 0);
  
  // Add a button
  lv_obj_t *btn = lv_btn_create(cont);
  lv_obj_set_size(btn, 120, 50);
  lv_obj_align(btn, LV_ALIGN_BOTTOM_MID, 0, -30);
  lv_obj_set_style_bg_color(btn, lv_color_hex(0x0066CC), 0);
  
  // Add button label
  lv_obj_t *btn_label = lv_label_create(btn);
  lv_label_set_text(btn_label, "Test");
  lv_obj_center(btn_label);
  lv_obj_set_style_text_color(btn_label, lv_color_hex(0xFFFFFF), 0);
  
  // Add button event
  lv_obj_add_event_cb(btn, [](lv_event_t *e) {
    lv_obj_t *btn = lv_event_get_target(e);
    lv_obj_t *label = lv_obj_get_child(btn, 0);
    static bool pressed = false;
    pressed = !pressed;
    lv_label_set_text(label, pressed ? "Pressed!" : "Test");
    Serial.println(pressed ? "Button pressed!" : "Button released!");
  }, LV_EVENT_CLICKED, NULL);
  
  // Add a progress bar
  lv_obj_t *bar = lv_bar_create(cont);
  lv_obj_set_size(bar, 300, 25);
  lv_obj_align(bar, LV_ALIGN_BOTTOM_MID, 0, -80);
  lv_bar_set_value(bar, 75, LV_ANIM_ON);
  lv_obj_set_style_bg_color(bar, lv_color_hex(0x333333), LV_PART_MAIN);
  lv_obj_set_style_bg_color(bar, lv_color_hex(0x00AAFF), LV_PART_INDICATOR);
  
  // Add progress label
  lv_obj_t *bar_label = lv_label_create(cont);
  lv_label_set_text(bar_label, "Progress: 75%");
  lv_obj_set_style_text_color(bar_label, lv_color_hex(0xCCCCCC), 0);
  lv_obj_align(bar_label, LV_ALIGN_BOTTOM_MID, 0, -50);
  
  Serial.println("Test UI created successfully!");
}
