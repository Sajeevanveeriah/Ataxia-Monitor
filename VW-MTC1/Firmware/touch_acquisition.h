// ADS8344NB protocol and hardware-capture accounting, independent of ESP-IDF.
#pragma once
#include "touch_decoder.h"
#include <array>
#include <cstddef>
#include <cstdint>

namespace vw_mtc1 {

// External-clock, single-ended channels 0,1,2,3. Channel-select bits are not
// binary channel order: TI SBAS139E, tables I/III/V and figures 3/5.
inline constexpr std::array<std::uint8_t, 13> touch_command{
    0x87, 0, 0, 0xc7, 0, 0, 0x97, 0, 0, 0xd7, 0, 0, 0
};

inline bool decode_touch_burst(const std::uint8_t* received, std::size_t size,
                              std::array<std::uint16_t, 4>& codes) {
    if (!received || size != touch_command.size()) return false;
    for (unsigned b : {3u, 6u, 9u, 12u})
        if (received[b] & 0x7fu) return false; // Required zero-filled clocks.
    for (unsigned ch = 0; ch < 4; ++ch) {
        const unsigned b = 3 * ch + 1;
        // The LSB arrives on clock 25, overlapping the next control byte.
        // The thirteenth byte is essential for channel 3's final bit.
        codes[ch] = std::uint16_t(((received[b] & 0x7fu) << 9) |
                                 (received[b + 1] << 1) |
                                 (received[b + 2] >> 7));
    }
    return true;
}

class CaptureClock {
public:
    std::uint64_t extend(std::uint32_t raw) {
        if (seen_ && raw < last_) epoch_ += std::uint64_t(1) << 32;
        last_ = raw;
        seen_ = true;
        return epoch_ + raw;
    }
private:
    bool seen_ = false;
    std::uint32_t last_ = 0;
    std::uint64_t epoch_ = 0;
};

struct BurstCapture {
    std::uint64_t carrier_edge_ticks = 0;
    std::uint64_t cs_fall_ticks = 0;
    std::uint64_t cs_rise_ticks = 0;
    std::uint32_t last_clock_fall = 0;
    std::uint32_t capture_hz = 0;
    std::uint32_t ticks_per_spi_clock = 0;
    bool excitation_high = false;
};

inline std::uint64_t capture_nanoseconds(std::uint64_t ticks, std::uint32_t hz) {
    // Multiplying the entire 80 MHz tick counter by 1e9 overflows in minutes.
    return hz ? (ticks / hz) * 1000000000ull + (ticks % hz) * 1000000000ull / hz : 0;
}

inline bool captured_frame(const BurstCapture& timing,
                           const std::uint8_t* received, std::size_t size,
                           TouchFrame& frame) {
    if (timing.capture_hz == 0 || timing.ticks_per_spi_clock == 0 ||
        timing.cs_rise_ticks <= timing.cs_fall_ticks) return false;
    // SCLK capture need not interrupt at 2 MHz: read its final falling edge
    // after the complete 104-clock burst, while the SPI bus remains owned.
    const auto elapsed = std::uint32_t(timing.last_clock_fall -
                                      std::uint32_t(timing.cs_fall_ticks));
    const std::uint64_t last_clock = timing.cs_fall_ticks + elapsed;
    const auto period = timing.ticks_per_spi_clock;
    if (timing.capture_hz / period != 2000000) return false;
    if (elapsed < 103 * period || elapsed > 108 * period ||
        last_clock > timing.cs_rise_ticks ||
        timing.cs_rise_ticks - last_clock > 4 * period) return false;
    // First hold is clock 8 falling; the final falling edge is clock 104.
    const std::uint64_t first_sample = last_clock - 96 * period;
    if (first_sample < timing.carrier_edge_ticks) return false;
    const auto phase_ticks = first_sample - timing.carrier_edge_ticks;
    if (phase_ticks >= timing.capture_hz / 2000) return false;
    const auto phase_ns = capture_nanoseconds(phase_ticks, timing.capture_hz);
    const auto last_phase_ns = phase_ns + 72ull * period * 1000000000ull /
                                         timing.capture_hz;
    if (phase_ns < 445000 || phase_ns > 455000 || last_phase_ns >= 500000)
        return false;
    if (!decode_touch_burst(received, size, frame.adc)) return false;
    frame.time_ns = capture_nanoseconds(first_sample, timing.capture_hz);
    frame.excitation_high = timing.excitation_high;
    return true;
}

}  // namespace vw_mtc1
