// VW-MTC1 synchronous touch decoder. No heap, SDK or hardware dependencies.
// Four ADC channels: wire, start, finish, unloaded reference bridge.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>

namespace vw_mtc1 {

struct TouchFrame {
    std::array<std::uint16_t, 4> adc{};
    std::uint64_t time_ns = 0;  // Hardware-captured time of the first acquisition.
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
            if (code < 1024 || code > 64511) {
                reset();
                return {};
            }
        }
        if (count_ && (frame.time_ns <= last_time_ ||
                       frame.time_ns - last_time_ < 488000 ||
                       frame.time_ns - last_time_ > 512000 ||
                       frame.excitation_high == last_high_)) {
            reset();
            return {};
        }
        if (!count_) first_time_ = frame.time_ns;
        last_time_ = frame.time_ns;
        last_high_ = frame.excitation_high;
        for (unsigned i = 0; i < 3; ++i) {
            history_[i] = history_[i + 1];
            times_[i] = times_[i + 1];
        }
        history_[3] = frame.adc;
        times_[3] = frame.time_ns;
        if (count_ < 4) ++count_;
        if (count_ < 4) return {};

        // Reject DC and a 55 Hz sinusoid at the ACTUAL acquisition times.
        // The broad rejection around the notch covers 50 and 60 Hz. Fixed
        // sample-spacing coefficients turn timing jitter into false touch
        // amplitude when the electrode carries a large mains component.
        std::array<double, 4> sine{}, cosine{}, weights{}, amplitude{};
        constexpr double omega = 2 * 3.14159265358979323846 * 55;
        for (unsigned i = 0; i < 4; ++i) {
            const double angle = omega * double(times_[i] - times_[0]) * 1e-9;
            sine[i] = std::sin(angle);
            cosine[i] = std::cos(angle);
        }
        double norm = 0;
        for (unsigned i = 0; i < 4; ++i) {
            std::array<unsigned, 3> j{};
            unsigned k = 0;
            for (unsigned n = 0; n < 4; ++n) if (n != i) j[k++] = n;
            const auto a = j[0], b = j[1], c = j[2];
            weights[i] = (i % 2 ? -1.0 : 1.0) *
                (sine[a] * (cosine[b] - cosine[c]) +
                 sine[b] * (cosine[c] - cosine[a]) +
                 sine[c] * (cosine[a] - cosine[b]));
            norm += std::abs(weights[i]);
        }
        if (!std::isfinite(norm) || norm < 1e-9) {
            reset();
            return {};
        }
        const double scale = (weights[3] < 0 ? -8.0 : 8.0) / norm;
        const int phase = frame.excitation_high ? 1 : -1;
        for (unsigned ch = 0; ch < 4; ++ch) {
            for (unsigned i = 0; i < 4; ++i)
                amplitude[ch] += phase * scale * weights[i] * history_[i][ch];
        }
        // ADS8344NB: 16-bit data, approximately 9,000 codes of reference swing.
        // A stopped carrier, wrong phase or reference wiring fault fails closed
        // as "invalid", not as a fabricated touch or an open contact.
        const auto reference = amplitude[3];
        if (reference < 32000 || reference > 60000) {
            reset();
            return {};
        }
        if (frame.time_ns - first_time_ < std::uint64_t(warmup_us) * 1000) return {};

        const auto previous = contacts_;
        for (unsigned ch = 0; ch < 3; ++ch) {
            const auto bit = static_cast<std::uint8_t>(1u << ch);
            if (hold_[ch]) --hold_[ch];
            if (hold_[ch]) continue;
            const auto loss = 2000 * (reference - amplitude[ch]);
            if (!valid_) {
                if (loss >= 60 * reference) contacts_ |= bit;
                continue;  // Initial state is not an onset event.
            }
            const bool active = (contacts_ & bit) != 0;
            if ((!active && loss >= 60 * reference) || (active && loss <= 59 * reference)) {
                contacts_ ^= bit;
                // A release has an extra cable RC tail. Suppress that tail,
                // while keeping both transitions inside a 5 ms gap.
                hold_[ch] = active ? 8 : 4;
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
    std::array<std::uint64_t, 4> times_{};
    std::array<unsigned, 3> hold_{};
    unsigned count_ = 0;
    std::uint64_t first_time_ = 0;
    std::uint64_t last_time_ = 0;
    bool last_high_ = false;
    bool valid_ = false;
    std::uint8_t contacts_ = 0;
};

}  // namespace vw_mtc1
