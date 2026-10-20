// Rev B acquisition demonstrator. No BLE, Hall polling or actuator control.
// Bench-qualify timing on the populated board before integrating other tasks.
#include "touch_acquisition.h"
#include "vw_mtc1_pins.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include "driver/gpio.h"
#include "driver/mcpwm_prelude.h"
#include "driver/spi_master.h"
#include "esp_attr.h"
#include "esp_check.h"
#include "esp_rom_gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "hal/mcpwm_periph.h"

namespace {
constexpr auto exc_pin = gpio_num_t(PIN_TOUCH_EXC);
constexpr auto cs_pin = gpio_num_t(PIN_TOUCH_CS);
constexpr auto clock_pin = gpio_num_t(PIN_ADC_SCK);
portMUX_TYPE capture_lock = portMUX_INITIALIZER_UNLOCKED;
struct Edges {
    std::uint64_t carrier = 0;
    std::uint32_t carrier_raw = 0, carrier_sequence = 0;
    std::uint32_t cs_fall = 0, cs_rise = 0, cs_sequence = 0;
    bool high = false;
};
Edges captured;
mcpwm_cap_channel_handle_t clock_capture;
spi_device_handle_t adc;
std::uint32_t capture_hz;
QueueHandle_t reports;

bool IRAM_ATTR carrier_edge(mcpwm_cap_channel_handle_t,
                            const mcpwm_capture_event_data_t* event, void*) {
    portENTER_CRITICAL_ISR(&capture_lock);
    // This channel runs continuously at 2 kHz, so every 32-bit rollover is seen.
    captured.carrier += std::uint32_t(event->cap_value - captured.carrier_raw);
    captured.carrier_raw = event->cap_value;
    ++captured.carrier_sequence;
    captured.high = event->cap_edge == MCPWM_CAP_EDGE_POS;
    portEXIT_CRITICAL_ISR(&capture_lock);
    return false;
}

bool IRAM_ATTR cs_edge(mcpwm_cap_channel_handle_t,
                       const mcpwm_capture_event_data_t* event, void*) {
    portENTER_CRITICAL_ISR(&capture_lock);
    if (event->cap_edge == MCPWM_CAP_EDGE_NEG) captured.cs_fall = event->cap_value;
    else captured.cs_rise = event->cap_value;
    ++captured.cs_sequence;
    portEXIT_CRITICAL_ISR(&capture_lock);
    return false;
}

Edges snapshot() {
    portENTER_CRITICAL(&capture_lock);
    const auto value = captured;
    portEXIT_CRITICAL(&capture_lock);
    return value;
}

// Only call while no SPI transaction is in progress. Software capture replaces
// the SCLK latch; the real last clock edge MUST be read before calling this.
std::uint32_t now_ticks() {
    std::uint32_t ticks = 0;
    ESP_ERROR_CHECK(mcpwm_capture_channel_trigger_soft_catch(clock_capture));
    ESP_ERROR_CHECK(mcpwm_capture_get_latched_value(clock_capture, &ticks));
    return ticks;
}

struct Report {
    std::uint32_t frames = 0, rejected = 0, valid = 0;
    std::uint32_t pressed[3]{}, released[3]{};
    std::uint32_t max_delivery_us = 0;
    std::uint8_t contacts = 0;
};

void acquisition(void*) {
    vw_mtc1::TouchDecoder decoder;
    Report report;
    std::uint32_t previous_edge = 0;
    const auto ticks_per_us = capture_hz / 1000000;
    int kick_us = 440;  // Calibrated against captured SCLK, never assumed.
    alignas(4) std::uint8_t tx[16]{}, rx[16]{};
    std::memcpy(tx, vw_mtc1::touch_command.data(), vw_mtc1::touch_command.size());
    spi_transaction_t transaction{};
    transaction.length = 104;
    transaction.tx_buffer = tx;
    transaction.rx_buffer = rx;
    for (;;) {
        const auto edge = snapshot();
        if (!edge.carrier_sequence || edge.carrier_sequence == previous_edge)
            continue;
        auto phase = std::uint32_t(now_ticks() - edge.carrier_raw);
        if (phase < 350 * ticks_per_us) continue;
        previous_edge = edge.carrier_sequence;
        ++report.frames;
        bool valid = false;
        vw_mtc1::TouchFrame frame{};
        vw_mtc1::TouchResult result{};
        // Reserve the bus from phase 350 us through the end of the burst.
        // Future Hall transactions must fit outside this reserved interval.
        // ESP-IDF 6.1 rejects finite acquire timeouts, including zero. This
        // standalone app is the sole SPI client. Recheck phase after locking
        // so a future competing client cannot make us launch a late burst.
        if (phase < 430 * ticks_per_us &&
            spi_device_acquire_bus(adc, portMAX_DELAY) == ESP_OK) {
            phase = std::uint32_t(now_ticks() - edge.carrier_raw);
            if (phase >= 430 * ticks_per_us) {
                spi_device_release_bus(adc);
                decoder.reset();
                ++report.rejected;
                report.valid = 0;
                report.contacts = 0;
                if (report.frames % 2000 == 0) xQueueOverwrite(reports, &report);
                continue;
            }
            while ((phase = std::uint32_t(now_ticks() - edge.carrier_raw)) <
                   std::uint32_t(kick_us) * ticks_per_us) {}
            const auto before = snapshot();
            std::memset(rx, 0xff, sizeof(rx));
            const auto status = spi_device_polling_transmit(adc, &transaction);
            std::uint32_t last_clock = 0;
            ESP_ERROR_CHECK(mcpwm_capture_get_latched_value(clock_capture, &last_clock));
            // Give the final CS ISR a bounded opportunity to publish its latch.
            auto after = snapshot();
            const auto end = now_ticks();
            while (std::uint32_t(after.cs_sequence - before.cs_sequence) < 2 &&
                   std::uint32_t(now_ticks() - end) < 3 * ticks_per_us)
                after = snapshot();
            spi_device_release_bus(adc);

            vw_mtc1::BurstCapture timing{};
            timing.carrier_edge_ticks = edge.carrier;
            timing.cs_fall_ticks = edge.carrier +
                                  std::uint32_t(after.cs_fall - edge.carrier_raw);
            timing.cs_rise_ticks = timing.cs_fall_ticks +
                                  std::uint32_t(after.cs_rise - after.cs_fall);
            timing.last_clock_fall = last_clock;
            timing.capture_hz = capture_hz;
            timing.ticks_per_spi_clock = capture_hz / 2000000;
            timing.excitation_high = edge.high;
            valid = status == ESP_OK &&
                    before.carrier_sequence == edge.carrier_sequence &&
                    std::uint32_t(after.cs_sequence - before.cs_sequence) == 2 &&
                    vw_mtc1::captured_frame(timing, rx, 13, frame);
            if (status == ESP_OK) {
                const auto sample_phase = std::uint32_t(last_clock - edge.carrier_raw) -
                                          96 * timing.ticks_per_spi_clock;
                if (sample_phase < 550 * ticks_per_us) {
                    const int correction = int(sample_phase / ticks_per_us) - 450;
                    kick_us = std::clamp(kick_us - correction, 400, 446);
                }
            }
        }
        if (valid) {
            result = decoder.update(frame);
            const auto delivered = edge.carrier +
                                   std::uint32_t(now_ticks() - edge.carrier_raw);
            const auto delivery_ns = vw_mtc1::capture_nanoseconds(delivered, capture_hz);
            const auto age_ns = delivery_ns - frame.time_ns;
            // The simulation adds 48 us of serial transfer. This app also
            // bounds processing/scheduling, with a 150 us delivery ceiling.
            if (age_ns > 150000) valid = false;
            else report.max_delivery_us = std::max(report.max_delivery_us,
                                                    std::uint32_t(age_ns / 1000));
        }
        if (!valid) {
            decoder.reset();
            ++report.rejected;
            result = {};  // Invalid data must never generate a release.
        }
        report.valid = result.valid;
        report.contacts = result.contacts;
        for (unsigned ch = 0; ch < 3; ++ch) {
            report.pressed[ch] += (result.pressed >> ch) & 1;
            report.released[ch] += (result.released >> ch) & 1;
        }
        if (report.frames % 2000 == 0) xQueueOverwrite(reports, &report);
    }
}

void initialise() {
    gpio_config_t safe{};
    safe.pin_bit_mask = (1ull << PIN_ADC_CS) | (1ull << PIN_HALL_EN_N);
    safe.mode = GPIO_MODE_OUTPUT;
    ESP_ERROR_CHECK(gpio_config(&safe));
    ESP_ERROR_CHECK(gpio_set_level(gpio_num_t(PIN_ADC_CS), 1));
    ESP_ERROR_CHECK(gpio_set_level(gpio_num_t(PIN_HALL_EN_N), 1));
    ESP_ERROR_CHECK(gpio_set_direction(gpio_num_t(PIN_TOUCH_BUSY), GPIO_MODE_INPUT));
    spi_bus_config_t bus{};
    bus.mosi_io_num = PIN_ADC_MOSI;
    bus.miso_io_num = PIN_ADC_MISO;
    bus.sclk_io_num = PIN_ADC_SCK;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = 16;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_DISABLED));
    spi_device_interface_config_t device{};
    device.clock_speed_hz = 2000000;
    device.mode = 0;
    device.spics_io_num = PIN_TOUCH_CS;
    device.cs_ena_pretrans = 1;   // 500 ns exceeds the ADS8344 100 ns tCSS.
    device.cs_ena_posttrans = 1;
    device.input_delay_ns = 200; // Datasheet maximum DCLK-to-DOUT at 2.7 V.
    device.queue_size = 1;
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &device, &adc));
    mcpwm_timer_handle_t pwm;
    mcpwm_timer_config_t timer{};
    timer.group_id = 0;
    timer.clk_src = MCPWM_TIMER_CLK_SRC_DEFAULT;
    timer.resolution_hz = 1000000;
    timer.count_mode = MCPWM_TIMER_COUNT_MODE_UP;
    timer.period_ticks = 1000;
    ESP_ERROR_CHECK(mcpwm_new_timer(&timer, &pwm));
    mcpwm_oper_handle_t oper;
    mcpwm_operator_config_t operator_config{};
    operator_config.group_id = 0;
    ESP_ERROR_CHECK(mcpwm_new_operator(&operator_config, &oper));
    ESP_ERROR_CHECK(mcpwm_operator_connect_timer(oper, pwm));
    mcpwm_cmpr_handle_t compare;
    mcpwm_comparator_config_t comparator{};
    ESP_ERROR_CHECK(mcpwm_new_comparator(oper, &comparator, &compare));
    ESP_ERROR_CHECK(mcpwm_comparator_set_compare_value(compare, 500));
    mcpwm_gen_handle_t generator;
    mcpwm_generator_config_t generator_config{};
    generator_config.gen_gpio_num = exc_pin;
    ESP_ERROR_CHECK(mcpwm_new_generator(oper, &generator_config, &generator));
    ESP_ERROR_CHECK(gpio_set_drive_capability(exc_pin, GPIO_DRIVE_CAP_3));
    ESP_ERROR_CHECK(mcpwm_generator_set_action_on_timer_event(generator,
        MCPWM_GEN_TIMER_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP,
                                     MCPWM_TIMER_EVENT_EMPTY, MCPWM_GEN_ACTION_HIGH)));
    ESP_ERROR_CHECK(mcpwm_generator_set_action_on_compare_event(generator,
        MCPWM_GEN_COMPARE_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP,
                                       compare, MCPWM_GEN_ACTION_LOW)));
    mcpwm_cap_timer_handle_t capture_timer;
    mcpwm_capture_timer_config_t capture_config{};
    capture_config.group_id = 0;
    capture_config.clk_src = MCPWM_CAPTURE_CLK_SRC_DEFAULT;
    ESP_ERROR_CHECK(mcpwm_new_capture_timer(&capture_config, &capture_timer));
    ESP_ERROR_CHECK(mcpwm_capture_timer_get_resolution(capture_timer, &capture_hz));
    ESP_ERROR_CHECK(capture_hz % 2000000 == 0 ? ESP_OK : ESP_ERR_NOT_SUPPORTED);
    // This standalone app owns group 0 and allocates channels 0/1/2 in order.
    // Integrators must preserve that resource allocation.
    for (unsigned i = 0; i < 3; ++i) {
        mcpwm_cap_channel_handle_t channel;
        mcpwm_capture_channel_config_t channel_config{};
        channel_config.gpio_num = i == 0 ? exc_pin : i == 1 ? cs_pin : -1;
        channel_config.prescale = 1;
        channel_config.intr_priority = 3;
        channel_config.flags.pos_edge = i < 2;
        channel_config.flags.neg_edge = true;
        ESP_ERROR_CHECK(mcpwm_new_capture_channel(capture_timer, &channel_config, &channel));
        if (i < 2) {
            mcpwm_capture_event_callbacks_t callbacks{};
            callbacks.on_cap = i == 0 ? carrier_edge : cs_edge;
            ESP_ERROR_CHECK(mcpwm_capture_channel_register_event_callbacks(channel, &callbacks, nullptr));
        } else {
            clock_capture = channel;
            // Preserve native SPI IOMUX on GPIO12. Passing GPIO12 to the
            // capture driver remuxes its output away from SPI. Connect input.
            ESP_ERROR_CHECK(gpio_input_enable(clock_pin));
            esp_rom_gpio_connect_in_signal(clock_pin,
                soc_mcpwm_signals[0].captures[2].cap_sig, false);
            // No SCLK ISR: latch 2 MHz edges entirely in hardware.
        }
        ESP_ERROR_CHECK(mcpwm_capture_channel_enable(channel));
    }
    ESP_ERROR_CHECK(mcpwm_capture_timer_enable(capture_timer));
    ESP_ERROR_CHECK(mcpwm_capture_timer_start(capture_timer));
    ESP_ERROR_CHECK(mcpwm_timer_enable(pwm));
    ESP_ERROR_CHECK(mcpwm_timer_start_stop(pwm, MCPWM_TIMER_START_NO_STOP));
}
}  // namespace

extern "C" void app_main() {
    initialise();
    reports = xQueueCreate(1, sizeof(Report));
    configASSERT(reports);
    configASSERT(xTaskCreatePinnedToCore(acquisition, "touch", 6144, nullptr,
                                        configMAX_PRIORITIES - 2, nullptr, 1) == pdPASS);
    Report report;
    for (;;) {
        if (xQueueReceive(reports, &report, portMAX_DELAY)) {
            std::printf("frames=%lu rejected=%lu valid=%lu contacts=%u "
                        "press=%lu,%lu,%lu release=%lu,%lu,%lu max_age_us=%lu\n",
                (unsigned long)report.frames, (unsigned long)report.rejected,
                (unsigned long)report.valid, report.contacts,
                (unsigned long)report.pressed[0], (unsigned long)report.pressed[1],
                (unsigned long)report.pressed[2], (unsigned long)report.released[0],
                (unsigned long)report.released[1], (unsigned long)report.released[2],
                (unsigned long)report.max_delivery_us);
        }
    }
}
