#include "../VW-MTC1/Firmware/touch_acquisition.h"
#include <cstdlib>
#include <iostream>
#include <string>

using vw_mtc1::TouchDecoder;
using vw_mtc1::TouchFrame;
using vw_mtc1::TouchResult;

// Exit directly on failure, avoiding a Windows crash-report dialog.
#define assert(condition) do { if (!(condition)) { \
    std::cerr << "FAIL line " << __LINE__ << ": " << #condition << '\n'; \
    std::exit(1); }} while (false)

TouchFrame sample(unsigned n, unsigned mask = 0) {
    const bool high = n % 2 == 0;
    TouchFrame frame{{}, 450000ull + 500000ull * n, high};
    for (unsigned ch = 0; ch < 4; ++ch) {
        // 4% carrier loss for a grounded contact. A common DC offset is
        // intentionally different from the reference and must cancel out.
        const bool touched = ch < 3 && (mask & (1u << ch));
        frame.adc[ch] = static_cast<std::uint16_t>(
            high ? (touched ? 26250 : 27392) : (touched ? 17602 : 18368));
    }
    return frame;
}

void regressions() {
    TouchDecoder decoder;
    TouchResult result;
    unsigned presses = 0, releases = 0;
    bool open_in_gap = false;
    for (unsigned n = 0; n < 220; ++n) {
        const bool touched = (n >= 40 && n < 44) ||
                             (n >= 60 && n < 64) ||
                             (n >= 74 && n < 78) ||
                             (n >= 100 && n < 140) ||
                             (n >= 150 && n < 190);
        result = decoder.update(sample(n, touched ? 7 : 0));
        if (n < 10) assert(!result.valid);
        if (result.pressed == 7) ++presses;
        if (result.released == 7) ++releases;
        if (n >= 140 && n < 150 && result.valid && result.contacts == 0)
            open_in_gap = true;
    }
    assert(result.valid && result.contacts == 0);
    assert(presses == 5 && releases == 5 && open_in_gap);

    // Each channel is independent, and a held contact at power-up is a state,
    // not a new user event.
    for (unsigned mask = 1; mask < 8; ++mask) {
        decoder.reset();
        for (unsigned n = 0; n < 30; ++n) {
            result = decoder.update(sample(n, mask));
            assert(result.pressed == 0 && result.released == 0);
        }
        assert(result.valid && result.contacts == mask);
    }

    // A missing frame, repeated carrier phase and rail-clipped ADC data each
    // invalidate acquisition and require a complete warm-up before recovery.
    for (unsigned fault = 0; fault < 4; ++fault) {
        decoder.reset();
        for (unsigned n = 0; n < 30; ++n) decoder.update(sample(n, 7));
        auto broken = sample(30, 7);
        if (fault == 0) broken.time_ns += 500000;
        if (fault == 1) broken.excitation_high = false;
        if (fault == 2) broken.adc[0] = 65535;
        if (fault == 3) broken.adc[3] = 100;
        result = decoder.update(broken);
        assert(!result.valid && result.pressed == 0 && result.released == 0);
        for (unsigned n = 31; n < 41; ++n) assert(!decoder.update(sample(n)).valid);
        result = decoder.update(sample(41));
        assert(result.valid && result.contacts == 0 && result.pressed == 0);
    }
    decoder.reset();
    for (unsigned n = 0; n < 30; ++n) decoder.update(sample(n, 7));
    for (unsigned n = 30; n < 34; ++n) {
        auto stopped = sample(n, 7);
        stopped.adc[3] = 2048;
        result = decoder.update(stopped);
    }
    assert(!result.valid);

    // Known open contact with a large 50/60 Hz component and alternating
    // acquisition jitter. A fixed-spacing differentiator converts that jitter
    // into false carrier loss; timestamp-aware rejection must remain open.
    for (double frequency : {48., 50., 60., 62.}) {
        decoder.reset();
        for (unsigned n = 0; n < 1000; ++n) {
            auto frame = sample(n);
            if (n % 2) frame.time_ns += 5000;
            else frame.time_ns -= 5000;
            const double t = double(frame.time_ns) * 1e-9;
            const double sign = frame.excitation_high ? 1 : -1;
            for (unsigned ch = 0; ch < 3; ++ch) {
                const double hum = 11000 * std::sin(2 * 3.14159265358979323846 * frequency * t + ch);
                frame.adc[ch] = std::uint16_t(std::lround(22880 + sign * 4512 * .976 + hum));
            }
            result = decoder.update(frame);
            if (result.valid) assert(result.contacts == 0 && result.pressed == 0);
        }
    }
}

void acquisition_tests() {
    using namespace vw_mtc1;
    const std::array<std::uint16_t,4> expected{0x8000,0x1234,0xffff,0x0001};
    std::array<std::uint8_t,13> bytes{};
    for (unsigned ch=0;ch<4;++ch) {
        const auto b=3*ch+1;
        bytes[b] |= (expected[ch] >> 9) & 0x7f;
        bytes[b+1] = (expected[ch] >> 1) & 0xff;
        bytes[b+2] |= (expected[ch] & 1) << 7;
    }
    std::array<std::uint16_t,4> decoded{};
    assert(decode_touch_burst(bytes.data(),bytes.size(),decoded) && decoded==expected);
    assert(!decode_touch_burst(bytes.data(),12,decoded));
    assert(!decode_touch_burst(nullptr,13,decoded));
    bytes[12] |= 1;
    assert(!decode_touch_burst(bytes.data(),13,decoded));
    bytes[12] &= ~1u;
    assert(touch_command[0]==0x87 && touch_command[3]==0xc7 &&
           touch_command[6]==0x97 && touch_command[9]==0xd7);

    CaptureClock clock;
    assert(clock.extend(0xfffffff0u)==0xfffffff0ull);
    assert(clock.extend(20)==(1ull<<32)+20);
    assert(clock.extend(40)==(1ull<<32)+40);
    assert(capture_nanoseconds(80'000'000ull*3600,80'000'000)==3'600'000'000'000ull);

    // 2 MHz SPI, 80 MHz capture. Includes a 32-bit capture-counter wrap.
    const std::uint64_t base=(1ull<<32)-12000;
    BurstCapture capture{base,base+35640,base+39880,
                         std::uint32_t(base+39840),80000000,40,true};
    TouchFrame frame;
    assert(captured_frame(capture,bytes.data(),bytes.size(),frame));
    assert(frame.adc==expected && frame.excitation_high);
    assert(frame.time_ns==capture_nanoseconds(base+36000,80000000));
    capture.last_clock_fall-=8*40; // A missing byte is not a complete conversion.
    assert(!captured_frame(capture,bytes.data(),bytes.size(),frame));
    capture.last_clock_fall+=8*40;
    capture.carrier_edge_ticks-=4000; // Sampling after the permitted phase.
    assert(!captured_frame(capture,bytes.data(),bytes.size(),frame));
    capture.capture_hz=0;
    assert(!captured_frame(capture,bytes.data(),bytes.size(),frame));
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--replay") {
        TouchDecoder decoder;
        unsigned high, a, b, c, reference;
        std::uint64_t time;
        while (std::cin >> time >> high >> a >> b >> c >> reference) {
            // time=0 is an explicit independent-simulation boundary.
            if (time == 0) { decoder.reset(); continue; }
            const auto result = decoder.update(TouchFrame{{
                static_cast<std::uint16_t>(a), static_cast<std::uint16_t>(b),
                static_cast<std::uint16_t>(c), static_cast<std::uint16_t>(reference)},
                time, high != 0});
            std::cout << time << ' ' << result.valid << ' '
                      << unsigned(result.contacts) << ' '
                      << unsigned(result.pressed) << ' '
                      << unsigned(result.released) << '\n';
        }
        return 0;
    }
    regressions();
    acquisition_tests();
    std::cout << "Touch decoder/acquisition: timing, events, jitter, SPI framing and capture rollover tests passed\n";
}
