// VW-MTC1 synchronous touch decoder. No heap, SDK or hardware dependencies.
// Four ADC channels: wire, start, finish, unloaded reference bridge.
#pragma once

#include <array>
#include <cstdint>

namespace vw_mtc1 {

struct TouchFrame {
    std::array<std::uint16_t, 4> adc{};
    std::uint64_t time_us = 0;  // Time of the first acquisition in this burst.
    bool excitation_high = false;
};

struct TouchResult {
    bool valid = false;
    std::uint8_t contacts = 0;
    std::uint8_t pressed = 0;
    std::uint8_t released = 0;
};

class TouchDecoder {
public:
    // The analogue and timing acceptance envelope is documented with the design.
    static constexpr unsigned sample_period_us = 500;
    static constexpr unsigned warmup_us = 5000;

    void reset() { *this = TouchDecoder{}; }

    TouchResult update(const TouchFrame& frame) {
        // A bad frame invalidates the state. It must never manufacture a release
        // event or let a stale contact state masquerade as a fresh measurement.
        for (const auto code : frame.adc) {
            if (code < 64 || code > 4031) {
                reset();
                return {};
            }
        }
        if (count_ && (frame.time_us <= last_time_ ||
                       frame.time_us - last_time_ < 494 ||
                       frame.time_us - last_time_ > 506 ||
                       frame.excitation_high == last_high_)) {
            reset();
            return {};
        }
        if (!count_) first_time_ = frame.time_us;
        last_time_ = frame.time_us;
        last_high_ = frame.excitation_high;
        for (unsigned i = 0; i < 3; ++i) history_[i] = history_[i + 1];
        history_[3] = frame.adc;
        if (count_ < 4) ++count_;
        if (count_ < 4) return {};

        std::array<std::int32_t, 4> amplitude{};
        const int phase = frame.excitation_high ? 1 : -1;
        for (unsigned ch = 0; ch < 4; ++ch) {
            amplitude[ch] = phase * (-std::int32_t(history_[0][ch]) +
                3 * std::int32_t(history_[1][ch]) -
                3 * std::int32_t(history_[2][ch]) +
                std::int32_t(history_[3][ch]));
        }
        // Expected reference result is 4 * (0.75 - 0.25) * 4096 = 8192.
        // A stopped carrier, wrong phase or reference wiring fault fails closed
        // as "invalid", not as a fabricated touch or an open contact.
        const auto reference = amplitude[3];
        if (reference < 6000 || reference > 10000) {
            reset();
            return {};
        }
        if (frame.time_us - first_time_ < warmup_us) return {};

        const auto previous = contacts_;
        for (unsigned ch = 0; ch < 3; ++ch) {
            const auto bit = static_cast<std::uint8_t>(1u << ch);
            if (hold_[ch]) --hold_[ch];
            if (hold_[ch]) continue;
            const auto loss = 1000 * (reference - amplitude[ch]);
            const bool active = (contacts_ & bit) != 0;
            if ((!active && loss >= 31 * reference) ||
                (active && loss <= 29 * reference)) {
                contacts_ ^= bit;
                // Four half cycles suppress the contact-step transient without
                // joining contacts separated by a 5 ms open interval.
                hold_[ch] = 4;
            }
        }
        const bool was_valid = valid_;
        valid_ = true;
        return {true, contacts_,
                static_cast<std::uint8_t>(was_valid ? contacts_ & ~previous : 0),
                static_cast<std::uint8_t>(was_valid ? previous & ~contacts_ : 0)};
    }

private:
    std::array<std::array<std::uint16_t, 4>, 4> history_{};
    std::array<unsigned, 3> hold_{};
    unsigned count_ = 0;
    std::uint64_t first_time_ = 0;
    std::uint64_t last_time_ = 0;
    bool last_high_ = false;
    bool valid_ = false;
    std::uint8_t contacts_ = 0;
};

}  // namespace vw_mtc1
