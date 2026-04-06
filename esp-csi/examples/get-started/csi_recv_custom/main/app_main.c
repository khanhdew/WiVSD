/*
 * SPDX-FileCopyrightText: 2025-2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/* Get Start Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "nvs_flash.h"

#include "esp_mac.h"
#include "rom/ets_sys.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_csi_gain_ctrl.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

#define CONFIG_LESS_INTERFERENCE_CHANNEL   13
#if CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C61 || (CONFIG_IDF_TARGET_ESP32C6 && ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 4, 0))
#define CONFIG_WIFI_BAND_MODE               WIFI_BAND_MODE_2G_ONLY
#define CONFIG_WIFI_2G_BANDWIDTHS           WIFI_BW_HT40
#define CONFIG_WIFI_5G_BANDWIDTHS           WIFI_BW_HT40
#define CONFIG_WIFI_2G_PROTOCOL             WIFI_PROTOCOL_11N
#define CONFIG_WIFI_5G_PROTOCOL             WIFI_PROTOCOL_11N
#else
#define CONFIG_WIFI_BANDWIDTH           WIFI_BW_HT40
#endif

#define CONFIG_ESP_NOW_PHYMODE           WIFI_PHY_MODE_HT40
#define CONFIG_ESP_NOW_RATE             WIFI_PHY_RATE_MCS0_LGI
#define CONFIG_FORCE_GAIN                   0

// Binary output mode: 0=CSV (text), 1=Binary compact, 2=Binary + header
#define CONFIG_OUTPUT_MODE                  0

#if CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C61
#define CSI_FORCE_LLTF                      0
#endif

#if CONFIG_IDF_TARGET_ESP32S3 || CONFIG_IDF_TARGET_ESP32C3 || CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C6 || CONFIG_IDF_TARGET_ESP32C61
#define CONFIG_GAIN_CONTROL                 1
#endif

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(6, 0, 0)
#define ESP_IF_WIFI_STA ESP_MAC_WIFI_STA
#endif

#if (CONFIG_IDF_TARGET_ESP32C6 && ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 4, 0))
#define CONFIG_WIFI_BAND_MODE               WIFI_BAND_MODE_2G_ONLY
#define CONFIG_WIFI_2G_BANDWIDTHS           WIFI_BW_HT20
#define CONFIG_WIFI_2G_PROTOCOL             WIFI_PROTOCOL_11AX
#define CONFIG_ESP_NOW_PHYMODE           WIFI_PHY_MODE_HE20
#define CONFIG_ESP_NOW_RATE             WIFI_PHY_RATE_MCS0_LGI
#define CONFIG_FORCE_GAIN                   1
#endif

static const uint8_t CONFIG_CSI_SEND_MAC[] = {0x1a, 0x00, 0x00, 0x00, 0x00, 0x00};
static const char *TAG = "csi_recv";

// Binary CSI packet structure for optimized UART transmission
#pragma pack(1)
typedef struct {
    uint8_t magic[2];           // 0xAA, 0xBB = header marker
    uint8_t version;            // Protocol version
    uint8_t chip_type;          // 0=ESP32, 1=ESP32C6, 2=ESP32C5, etc.
    uint32_t sequence;          // Packet sequence number
    uint8_t mac[6];             // Source MAC address
    int8_t rssi;                // RSSI
    uint8_t rate;               // Data rate
    int8_t noise_floor;         // Noise floor
    int8_t fft_gain;            // FFT gain
    uint8_t agc_gain;           // AGC gain
    uint8_t channel;            // Wi-Fi channel
    uint16_t timestamp_lo;      // Local timestamp (lower 16 bits)
    uint16_t timestamp_hi;      // Local timestamp (upper 16 bits)
    uint16_t sig_len;           // Signal length
    uint16_t rx_state;          // RX state
    uint16_t csi_len;           // Number of CSI subcarriers
    uint8_t first_word_invalid; // First word valid flag
    uint8_t reserved;           // Reserved for alignment
    // CSI data follows: int8_t csi_data[csi_len]
} csi_binary_header_t;
#pragma pack()

_Static_assert(sizeof(csi_binary_header_t) == 32, "Header must be exactly 32 bytes");

static volatile uint32_t g_csi_seq_num = 0;

/* ---- Queue-based CSI offload: raw data is copied in the callback,
        formatted/printed in a dedicated task ---- */
#define CSI_BUF_MAX     512
#define CSI_QUEUE_DEPTH 16

typedef struct {
    uint8_t  mac[6];
    int8_t   rssi;
    uint8_t  rate;
    int8_t   noise_floor;
    int8_t   fft_gain;
    uint8_t  agc_gain;
    uint8_t  channel;
    uint32_t timestamp;
    uint16_t sig_len;
    uint16_t rx_state;
#if !(CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C6 || CONFIG_IDF_TARGET_ESP32C61)
    uint8_t  sig_mode;
    uint8_t  mcs;
    uint8_t  cwb;
    uint8_t  smoothing;
    uint8_t  not_sounding;
    uint8_t  aggregation;
    uint8_t  stbc;
    uint8_t  fec_coding;
    uint8_t  sgi;
    uint16_t ampdu_cnt;
    uint8_t  secondary_channel;
    uint8_t  ant;
#endif
    float    compensate_gain;
    uint32_t rx_id;
    uint32_t seq_num;
    uint16_t csi_len;
    uint8_t  first_word_invalid;
    int8_t   csi_buf[CSI_BUF_MAX];
} csi_data_item_t;

/* Static pool + two pointer-queues avoid large copies and heap alloc in cb */
static csi_data_item_t s_csi_pool[CSI_QUEUE_DEPTH];
static QueueHandle_t   s_csi_free_q = NULL;   /* pool of available slots  */
static QueueHandle_t   s_csi_data_q = NULL;   /* filled slots for printer */

static void wifi_init()
{
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(esp_netif_init());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));

#if CONFIG_IDF_TARGET_ESP32C5
    ESP_ERROR_CHECK(esp_wifi_start());
    esp_wifi_set_band_mode(CONFIG_WIFI_BAND_MODE);
    wifi_protocols_t protocols = {
        .ghz_2g = CONFIG_WIFI_2G_PROTOCOL,
        .ghz_5g = CONFIG_WIFI_5G_PROTOCOL
    };
    ESP_ERROR_CHECK(esp_wifi_set_protocols(ESP_IF_WIFI_STA, &protocols));
    wifi_bandwidths_t bandwidth = {
        .ghz_2g = CONFIG_WIFI_2G_BANDWIDTHS,
        .ghz_5g = CONFIG_WIFI_5G_BANDWIDTHS
    };
    ESP_ERROR_CHECK(esp_wifi_set_bandwidths(ESP_IF_WIFI_STA, &bandwidth));
#elif (CONFIG_IDF_TARGET_ESP32C6 && ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 4, 0)) || CONFIG_IDF_TARGET_ESP32C61
    ESP_ERROR_CHECK(esp_wifi_start());
    esp_wifi_set_band_mode(CONFIG_WIFI_BAND_MODE);
    wifi_protocols_t protocols = {
        .ghz_2g = CONFIG_WIFI_2G_PROTOCOL,
    };
    ESP_ERROR_CHECK(esp_wifi_set_protocols(ESP_IF_WIFI_STA, &protocols));
    wifi_bandwidths_t bandwidth = {
        .ghz_2g = CONFIG_WIFI_2G_BANDWIDTHS,
    };
    ESP_ERROR_CHECK(esp_wifi_set_bandwidths(ESP_IF_WIFI_STA, &bandwidth));
#else
    ESP_ERROR_CHECK(esp_wifi_set_bandwidth(ESP_IF_WIFI_STA, CONFIG_WIFI_BANDWIDTH));
    ESP_ERROR_CHECK(esp_wifi_start());
#endif

    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
#if CONFIG_IDF_TARGET_ESP32C5
    if ((CONFIG_WIFI_BAND_MODE == WIFI_BAND_MODE_2G_ONLY && CONFIG_WIFI_2G_BANDWIDTHS == WIFI_BW_HT20)
            || (CONFIG_WIFI_BAND_MODE == WIFI_BAND_MODE_5G_ONLY && CONFIG_WIFI_5G_BANDWIDTHS == WIFI_BW_HT20)) {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_NONE));
    } else {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_BELOW));
    }
#elif (CONFIG_IDF_TARGET_ESP32C6 && ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 4, 0)) || CONFIG_IDF_TARGET_ESP32C61
    if (CONFIG_WIFI_BAND_MODE == WIFI_BAND_MODE_2G_ONLY && CONFIG_WIFI_2G_BANDWIDTHS == WIFI_BW_HT20) {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_NONE));
    } else {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_BELOW));
    }
#else
    if (CONFIG_WIFI_BANDWIDTH == WIFI_BW_HT20) {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_NONE));
    } else {
        ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_BELOW));
    }
#endif

    ESP_ERROR_CHECK(esp_wifi_set_mac(WIFI_IF_STA, CONFIG_CSI_SEND_MAC));
}

static void wifi_esp_now_init(esp_now_peer_info_t peer)
{
    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_set_pmk((uint8_t *)"pmk1234567890123"));
    esp_now_rate_config_t rate_config = {
        .phymode = CONFIG_ESP_NOW_PHYMODE,
        .rate = CONFIG_ESP_NOW_RATE,//  WIFI_PHY_RATE_MCS0_LGI,
        .ersu = false,
        .dcm = false
    };
    ESP_ERROR_CHECK(esp_now_add_peer(&peer));
    ESP_ERROR_CHECK(esp_now_set_peer_rate_config(peer.peer_addr, &rate_config));

}

static void wifi_csi_rx_cb(void *ctx, wifi_csi_info_t *info)
{
    if (!info || !info->buf) {
        ESP_LOGW(TAG, "<%s> wifi_csi_cb", esp_err_to_name(ESP_ERR_INVALID_ARG));
        return;
    }

    if (memcmp(info->mac, CONFIG_CSI_SEND_MAC, 6)) {
        return;
    }

    const wifi_pkt_rx_ctrl_t *rx_ctrl = &info->rx_ctrl;
    static int s_count = 0;
    float compensate_gain = 1.0f;
    static uint8_t agc_gain = 0;
    static int8_t fft_gain = 0;
#if CONFIG_GAIN_CONTROL
    static uint8_t agc_gain_baseline = 0;
    static int8_t fft_gain_baseline = 0;
    esp_csi_gain_ctrl_get_rx_gain(rx_ctrl, &agc_gain, &fft_gain);
    if (s_count < 100) {
        esp_csi_gain_ctrl_record_rx_gain(agc_gain, fft_gain);
    } else if (s_count == 100) {
        esp_csi_gain_ctrl_get_rx_gain_baseline(&agc_gain_baseline, &fft_gain_baseline);
#if CONFIG_FORCE_GAIN
        esp_csi_gain_ctrl_set_rx_force_gain(agc_gain_baseline, fft_gain_baseline);
        ESP_LOGD(TAG, "fft_force %d, agc_force %d", fft_gain_baseline, agc_gain_baseline);
#endif
    }
    esp_csi_gain_ctrl_get_gain_compensation(&compensate_gain, agc_gain, fft_gain);
    ESP_LOGD(TAG, "compensate_gain %f, agc_gain %d, fft_gain %d", compensate_gain, agc_gain, fft_gain);
#endif

    uint32_t rx_id = *(uint32_t *)(info->payload + 15);

    /* Grab a free slot from the pool (non-blocking) */
    csi_data_item_t *item = NULL;
    if (xQueueReceive(s_csi_free_q, &item, 0) != pdTRUE) {
        s_count++;
        return;  /* queue full – drop this frame */
    }

    /* Copy raw metadata – no string formatting here */
    memcpy(item->mac, info->mac, 6);
    item->rssi        = rx_ctrl->rssi;
    item->rate        = rx_ctrl->rate;
    item->noise_floor = rx_ctrl->noise_floor;
    item->fft_gain    = fft_gain;
    item->agc_gain    = agc_gain;
    item->channel     = rx_ctrl->channel;
    item->timestamp   = rx_ctrl->timestamp;
    item->sig_len     = rx_ctrl->sig_len;
    item->rx_state    = rx_ctrl->rx_state;
#if !(CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C6 || CONFIG_IDF_TARGET_ESP32C61)
    item->sig_mode          = rx_ctrl->sig_mode;
    item->mcs               = rx_ctrl->mcs;
    item->cwb               = rx_ctrl->cwb;
    item->smoothing         = rx_ctrl->smoothing;
    item->not_sounding      = rx_ctrl->not_sounding;
    item->aggregation       = rx_ctrl->aggregation;
    item->stbc              = rx_ctrl->stbc;
    item->fec_coding        = rx_ctrl->fec_coding;
    item->sgi               = rx_ctrl->sgi;
    item->ampdu_cnt         = rx_ctrl->ampdu_cnt;
    item->secondary_channel = rx_ctrl->secondary_channel;
    item->ant               = rx_ctrl->ant;
#endif
    item->compensate_gain    = compensate_gain;
    item->rx_id              = rx_id;
    item->seq_num            = g_csi_seq_num++;
    item->first_word_invalid = info->first_word_invalid;
    item->csi_len            = (info->len <= CSI_BUF_MAX) ? info->len : CSI_BUF_MAX;
    memcpy(item->csi_buf, info->buf, item->csi_len);

    /* Hand off to printer task (non-blocking) */
    if (xQueueSend(s_csi_data_q, &item, 0) != pdTRUE) {
        xQueueSend(s_csi_free_q, &item, 0);  /* return slot on failure */
    }

    s_count++;
}

/* ---------- Printer task – runs in its own FreeRTOS context ---------- */
static void csi_print_task(void *param)
{
    csi_data_item_t *item = NULL;
    bool header_printed = false;

    for (;;) {
        if (xQueueReceive(s_csi_data_q, &item, portMAX_DELAY) != pdTRUE) {
            continue;
        }

#if CONFIG_OUTPUT_MODE == 1 || CONFIG_OUTPUT_MODE == 2
        /* ============ BINARY MODE ============ */
        if (!header_printed) {
            ESP_LOGI(TAG, "================ CSI RECV (BINARY MODE) ================");
            header_printed = true;
        }

        csi_binary_header_t hdr = {
            .magic[0] = 0xAA,
            .magic[1] = 0xBB,
            .version = 1,
#if CONFIG_IDF_TARGET_ESP32C6
            .chip_type = 1,
#elif CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C61
            .chip_type = 2,
#else
            .chip_type = 0,
#endif
            .sequence = item->seq_num,
            .rssi = item->rssi,
            .rate = item->rate,
            .noise_floor = item->noise_floor,
            .fft_gain = item->fft_gain,
            .agc_gain = item->agc_gain,
            .channel = item->channel,
            .sig_len = item->sig_len,
            .rx_state = item->rx_state,
            .csi_len = item->csi_len,
            .first_word_invalid = item->first_word_invalid,
            .reserved = 0
        };
        memcpy(hdr.mac, item->mac, 6);
        hdr.timestamp_lo = (uint16_t)(item->timestamp & 0xFFFF);
        hdr.timestamp_hi = (uint16_t)((item->timestamp >> 16) & 0xFFFF);

        fwrite(&hdr, sizeof(csi_binary_header_t), 1, stdout);

#if CONFIG_OUTPUT_MODE == 2
        uint16_t sync = 0xBBAA;
        fwrite(&sync, 2, 1, stdout);
#endif

        for (int i = 0; i < item->csi_len; i++) {
            int16_t csi_val = (int16_t)(item->compensate_gain * item->csi_buf[i]);
            fwrite(&csi_val, sizeof(int16_t), 1, stdout);
        }

#if CONFIG_OUTPUT_MODE == 2
        fwrite(&sync, 2, 1, stdout);
#endif
        fflush(stdout);

#else
        /* ============ TEXT CSV MODE ============ */
        if (!header_printed) {
            ESP_LOGI(TAG, "================ CSI RECV ================");
#if CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C6 || CONFIG_IDF_TARGET_ESP32C61
            printf("type,seq,mac,rssi,rate,noise_floor,fft_gain,agc_gain,channel,local_timestamp,sig_len,rx_state,len,first_word,data\n");
#else
            printf("type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,local_timestamp,ant,sig_len,rx_state,len,first_word,data\n");
#endif
            header_printed = true;
        }

#if CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C6 || CONFIG_IDF_TARGET_ESP32C61
        printf("CSI_DATA,%ld," MACSTR ",%d,%d,%d,%d,%d,%d,%ld,%d,%d",
               item->rx_id, MAC2STR(item->mac), item->rssi, item->rate,
               item->noise_floor, item->fft_gain, item->agc_gain, item->channel,
               item->timestamp, item->sig_len, item->rx_state);
#else
        printf("CSI_DATA,%d," MACSTR ",%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
               item->rx_id, MAC2STR(item->mac), item->rssi, item->rate, item->sig_mode,
               item->mcs, item->cwb, item->smoothing, item->not_sounding,
               item->aggregation, item->stbc, item->fec_coding, item->sgi,
               item->noise_floor, item->ampdu_cnt, item->channel, item->secondary_channel,
               item->timestamp, item->ant, item->sig_len, item->rx_state);
#endif

#if (CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C61) && CSI_FORCE_LLTF
        {
            int16_t csi = ((int16_t)(((((uint16_t)item->csi_buf[1]) << 8) | item->csi_buf[0]) << 4) >> 4);
            printf(",%d,%d,\"[%d", (item->csi_len - 2) / 2, item->first_word_invalid,
                   (int16_t)(item->compensate_gain * csi));
            for (int i = 2; i < (item->csi_len - 2); i += 2) {
                csi = ((int16_t)(((((uint16_t)item->csi_buf[i + 1]) << 8) | item->csi_buf[i]) << 4) >> 4);
                printf(",%d", (int16_t)(item->compensate_gain * csi));
            }
        }
#else
        printf(",%d,%d,\"[%d", item->csi_len, item->first_word_invalid,
               (int16_t)(item->compensate_gain * item->csi_buf[0]));
        for (int i = 1; i < item->csi_len; i++) {
            printf(",%d", (int16_t)(item->compensate_gain * item->csi_buf[i]));
        }
#endif
        printf("]\"\n");

#endif  /* CONFIG_OUTPUT_MODE */

        /* Return slot to the free pool */
        xQueueSend(s_csi_free_q, &item, portMAX_DELAY);
    }
}

static void wifi_csi_init()
{
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));

    /**< default config */
#if CONFIG_IDF_TARGET_ESP32C5 || CONFIG_IDF_TARGET_ESP32C61
    wifi_csi_config_t csi_config = {
        .enable                   = true,
        .acquire_csi_legacy       = false,
        .acquire_csi_force_lltf   = CSI_FORCE_LLTF,
        .acquire_csi_ht20         = true,
        .acquire_csi_ht40         = true,
        .acquire_csi_vht          = false,
        .acquire_csi_su           = false,
        .acquire_csi_mu           = false,
        .acquire_csi_dcm          = false,
        .acquire_csi_beamformed   = false,
        .acquire_csi_he_stbc_mode = 2,
        .val_scale_cfg            = 0,
        .dump_ack_en              = false,
        .reserved                 = false
    };
#elif CONFIG_IDF_TARGET_ESP32C6
    wifi_csi_config_t csi_config = {
        .enable                 = true,
        .acquire_csi_legacy     = false,
        .acquire_csi_ht20       = false,
        .acquire_csi_ht40       = false,
        .acquire_csi_su         = true,
        .acquire_csi_mu         = true,
        .acquire_csi_dcm        = true,
        .acquire_csi_beamformed = true,
        .acquire_csi_he_stbc    = 2,
        .val_scale_cfg          = false,
        .dump_ack_en            = false,
        .reserved               = false
    };
#else
    wifi_csi_config_t csi_config = {
        .lltf_en           = true,
        .htltf_en          = true,
        .stbc_htltf2_en    = true,
        .ltf_merge_en      = true,
        .channel_filter_en = true,
        .manu_scale        = false,
        .shift             = false,
    };
#endif
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(wifi_csi_rx_cb, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
}

void app_main()
{
    /**
     * @brief Initialize NVS
     */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /**
     * @brief Initialize Wi-Fi
     */
    wifi_init();

    /**
     * @brief Initialize ESP-NOW
     *        ESP-NOW protocol see: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_now.html
     */

    esp_now_peer_info_t peer = {
        .channel   = CONFIG_LESS_INTERFERENCE_CHANNEL,
        .ifidx     = WIFI_IF_STA,
        .encrypt   = false,
        .peer_addr = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff},
    };

    wifi_esp_now_init(peer);

    /* Create CSI offload queues and seed the free pool */
    s_csi_free_q = xQueueCreate(CSI_QUEUE_DEPTH, sizeof(csi_data_item_t *));
    s_csi_data_q = xQueueCreate(CSI_QUEUE_DEPTH, sizeof(csi_data_item_t *));
    for (int i = 0; i < CSI_QUEUE_DEPTH; i++) {
        csi_data_item_t *slot = &s_csi_pool[i];
        xQueueSend(s_csi_free_q, &slot, portMAX_DELAY);
    }

    xTaskCreate(csi_print_task, "csi_print", 8192, NULL, 5, NULL);

    wifi_csi_init();
}
