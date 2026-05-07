/* CSI Reception with WiFi Provisioning Toggle Example

   This example demonstrates dual-mode operation:
   - Mode 1: CSI data reception (transmits as SoftAP)
   - Mode 2: WiFi provisioning via SoftAP

   Press GPIO button (default GPIO 9) to toggle between modes.

   This example code is in the public domain.
*/

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "driver/gpio.h"
#include "wifi_provisioning/wifi_config.h"
#include "wifi_provisioning/manager.h"
#include "wifi_provisioning/scheme_ble.h"
#include "sdkconfig.h"

// #include "esp_csi_gain_ctrl.h"

#define TAG "csi_prov_example"
#define PROV_BLE_SERVICE_NAME_PREFIX "CSI_PROV"

/* Mode definitions */
typedef enum {
    MODE_CSI_RECV = 0,
    MODE_PROVISIONING = 1,
    MODE_MAX
} app_mode_t;

/* Global state */
static app_mode_t current_mode = MODE_CSI_RECV;
static bool provisioned = false;
static EventGroupHandle_t mode_switch_event;
#define MODE_SWITCH_EVENT_BIT (1 << 0)
#define MODE_CHANGE_BIT (1 << 1)

static void app_wifi_provisioning_event_handler(void *arg, esp_event_base_t event_base,
                                                int32_t event_id, void *event_data);
static void app_wifi_event_handler(void *arg, esp_event_base_t event_base,
                                   int32_t event_id, void *event_data);

static void app_get_ble_service_name(char *service_name, size_t service_name_len)
{
    uint8_t eth_mac[6] = {0};

    ESP_ERROR_CHECK(esp_read_mac(eth_mac, ESP_MAC_WIFI_STA));
    snprintf(service_name, service_name_len, "%s_%02X%02X%02X",
             PROV_BLE_SERVICE_NAME_PREFIX, eth_mac[3], eth_mac[4], eth_mac[5]);
}

/* ============ GPIO Button Handler ============ */
static void IRAM_ATTR gpio_button_isr_handler(void *arg)
{
    static uint32_t last_press_time = 0;
    uint32_t current_time = xTaskGetTickCountFromISR();

    /* Debounce: 300ms */
    if ((current_time - last_press_time) > (300 / portTICK_PERIOD_MS)) {
        last_press_time = current_time;
        xEventGroupSetBitsFromISR(mode_switch_event, MODE_SWITCH_EVENT_BIT, NULL);
    }
}

static void app_init_button(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CONFIG_EXAMPLE_GPIO_BUTTON),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,  /* Trigger on falling edge */
    };

    ESP_ERROR_CHECK(gpio_config(&io_conf));
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(CONFIG_EXAMPLE_GPIO_BUTTON, gpio_button_isr_handler, NULL));
    
    ESP_LOGI(TAG, "Button configured on GPIO %d", CONFIG_EXAMPLE_GPIO_BUTTON);
}

/* ============ WiFi Event Handlers ============ */
static void app_wifi_event_handler(void *arg, esp_event_base_t event_base,
                                   int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
        case WIFI_EVENT_AP_STACONNECTED:
            ESP_LOGI(TAG, "STA connected to AP");
            break;
        case WIFI_EVENT_AP_STADISCONNECTED:
            ESP_LOGI(TAG, "STA disconnected from AP");
            break;
        case WIFI_EVENT_STA_START:
            ESP_LOGI(TAG, "STA started, attempting connection");
            break;
        case WIFI_EVENT_STA_CONNECTED:
            ESP_LOGI(TAG, "STA connected to AP");
            break;
        case WIFI_EVENT_STA_DISCONNECTED:
            ESP_LOGI(TAG, "STA disconnected from AP");
            break;
        default:
            break;
        }
    }
}

/* ============ WiFi Provisioning Event Handlers ============ */
static void app_wifi_provisioning_event_handler(void *arg, esp_event_base_t event_base,
                                                int32_t event_id, void *event_data)
{
    if (event_base == WIFI_PROV_EVENT) {
        switch (event_id) {
        case WIFI_PROV_START:
            ESP_LOGI(TAG, "Provisioning started");
            break;
        case WIFI_PROV_CRED_RECV: {
            wifi_sta_config_t *wifi_sta_cfg = (wifi_sta_config_t *)event_data;
            ESP_LOGI(TAG, "Credentials received: SSID=%s", (const char *)wifi_sta_cfg->ssid);
            break;
        }
        case WIFI_PROV_CRED_SUCCESS:
            ESP_LOGI(TAG, "Provisioning credentials accepted by WiFi");
            provisioned = true;
            break;
        case WIFI_PROV_END:
            ESP_LOGI(TAG, "Provisioning ended");
            break;
        case WIFI_PROV_DEINIT:
            ESP_LOGI(TAG, "Provisioning deinitialized");
            break;
        default:
            break;
        }
    }
}

/* ============ CSI Reception Mode ============ */
static void app_csi_reception_task(void *arg)
{
    ESP_LOGI(TAG, "Starting CSI reception mode");
    
    /* Initialize WiFi in SoftAP mode for CSI reception */
    wifi_mode_t mode;
    ESP_ERROR_CHECK(esp_wifi_get_mode(&mode));
    
    if (mode != WIFI_MODE_AP) {
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, NULL));
    }
    
    /* Configure SoftAP */
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = CONFIG_EXAMPLE_WIFI_SSID,
            .ssid_len = strlen(CONFIG_EXAMPLE_WIFI_SSID),
            .password = CONFIG_EXAMPLE_WIFI_PASS,
            .max_connection = CONFIG_EXAMPLE_MAX_STA_CONN,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    if (strlen(CONFIG_EXAMPLE_WIFI_PASS) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }
    
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_LOGI(TAG, "CSI Reception: SoftAP configured - SSID: %s", CONFIG_EXAMPLE_WIFI_SSID);
    
    /* Enable CSI reception on the SoftAP interface */
    wifi_csi_config_t csi_config = {
        .lltf_en = true,
        .htltf_en = false,
        .stbc_htltf2_en = false,
        .ltf_merge_en = false,
        .channel_filter_en = false,
        .manu_scale = false,
        .shift = false,
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(NULL, NULL));  /* Register CSI callback if needed */
    
    ESP_LOGI(TAG, "CSI reception active. Press button to switch to provisioning mode.");
    
    /* Stay in this mode until mode switch event */
    while (current_mode == MODE_CSI_RECV) {
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
    
    ESP_LOGI(TAG, "Exiting CSI reception mode");
    vTaskDelete(NULL);
}

/* ============ WiFi Provisioning Mode (BLE) ============ */
static void app_provisioning_task(void *arg)
{
    ESP_LOGI(TAG, "Starting WiFi provisioning mode");
    
    /* Initialize WiFi in SoftAP mode for provisioning */
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    
    /* Create default WiFi AP config */
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = CONFIG_EXAMPLE_WIFI_SSID,
            .ssid_len = strlen(CONFIG_EXAMPLE_WIFI_SSID),
            .password = CONFIG_EXAMPLE_WIFI_PASS,
            .max_connection = CONFIG_EXAMPLE_MAX_STA_CONN,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    if (strlen(CONFIG_EXAMPLE_WIFI_PASS) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }
    
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_LOGI(TAG, "Provisioning: SoftAP configured - SSID: %s", CONFIG_EXAMPLE_WIFI_SSID);
    
    /* Initialize provisioning manager with BLE scheme */
    wifi_prov_mgr_config_t config = {
        .scheme = wifi_prov_scheme_ble,
        .scheme_event_handler = WIFI_PROV_SCHEME_BLE_EVENT_HANDLER_FREE_BTDM,
    };
    
    ESP_ERROR_CHECK(wifi_prov_mgr_init(config));
    
    /* Register event handlers */
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_PROV_EVENT, ESP_EVENT_ANY_ID,
                                              &app_wifi_provisioning_event_handler, NULL));
    
    /* Check if already provisioned */
    bool provisioned = false;
    ESP_ERROR_CHECK(wifi_prov_mgr_is_provisioned(&provisioned));
    
    if (!provisioned) {
        ESP_LOGI(TAG, "Device not provisioned. Starting provisioning.");
        
        /* Start provisioning with security version */
        wifi_prov_security_t security = WIFI_PROV_SECURITY_0;
        
        if (CONFIG_EXAMPLE_PROV_SECURITY_VERSION == 1) {
            security = WIFI_PROV_SECURITY_1;
        } else if (CONFIG_EXAMPLE_PROV_SECURITY_VERSION == 2) {
            security = WIFI_PROV_SECURITY_2;
        }
        
        const char *pop = NULL;  /* Proof of Possession - NULL for no PoP */
        char service_name[24] = {0};

        app_get_ble_service_name(service_name, sizeof(service_name));
        ESP_LOGI(TAG, "Starting BLE provisioning service: %s", service_name);

        ESP_ERROR_CHECK(wifi_prov_mgr_start_provisioning(security, pop, service_name, NULL));
    } else {
        ESP_LOGI(TAG, "Device already provisioned. Attempting to connect.");
    }
    
    ESP_LOGI(TAG, "Provisioning mode active. Press button to switch to CSI reception mode.");
    
    /* Wait until provisioning is complete or mode switch */
    while (current_mode == MODE_PROVISIONING) {
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
    
    /* Cleanup provisioning */
    wifi_prov_mgr_deinit();
    ESP_LOGI(TAG, "Exiting provisioning mode");
    vTaskDelete(NULL);
}

/* ============ Mode Manager Task ============ */
static void mode_manager_task(void *arg)
{
    TaskHandle_t current_task = NULL;
    
    while (1) {
        /* Wait for mode switch event */
        EventBits_t bits = xEventGroupWaitBits(mode_switch_event, MODE_SWITCH_EVENT_BIT,
                                               pdTRUE, pdFALSE, portMAX_DELAY);
        
        if (bits & MODE_SWITCH_EVENT_BIT) {
            /* Kill existing mode task */
            if (current_task != NULL) {
                vTaskDelete(current_task);
                current_task = NULL;
                vTaskDelay(500 / portTICK_PERIOD_MS);  /* Give time for task cleanup */
            }
            
            /* Toggle mode */
            current_mode = (current_mode == MODE_CSI_RECV) ? MODE_PROVISIONING : MODE_CSI_RECV;
            ESP_LOGI(TAG, "Switching mode to: %s", 
                     current_mode == MODE_CSI_RECV ? "CSI Reception" : "Provisioning");
            
            /* Start new mode task */
            if (current_mode == MODE_CSI_RECV) {
                xTaskCreate(app_csi_reception_task, "csi_recv", 4096, NULL, 5, &current_task);
            } else {
                xTaskCreate(app_provisioning_task, "provisioning", 4096, NULL, 5, &current_task);
            }
        }
    }
}

/* ============ Application Initialization ============ */
void app_main(void)
{
    ESP_LOGI(TAG, "CSI with WiFi Provisioning Example started");
    
    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    /* Initialize networking stack */
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    /* Create default WiFi AP interface */
    esp_netif_create_default_wifi_ap();
    
    /* Initialize WiFi */
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    /* Register event handlers */
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                              &app_wifi_event_handler, NULL));
    
    /* Start WiFi */
    ESP_ERROR_CHECK(esp_wifi_start());
    
    /* Initialize button */
    app_init_button();
    
    /* Create event group for mode switching */
    mode_switch_event = xEventGroupCreate();
    
    /* Start mode manager task */
    xTaskCreate(mode_manager_task, "mode_mgr", 2048, NULL, 4, NULL);
    
    /* Start initial mode (CSI Reception) */
    xTaskCreate(app_csi_reception_task, "csi_recv", 4096, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "Application initialized successfully");
}
