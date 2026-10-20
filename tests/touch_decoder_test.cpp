#include "../VW-MTC1/Firmware/touch_decoder.h"
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
    TouchFrame frame{{}, 405u + 500u * n, high};
    for (unsigned ch = 0; ch < 4; ++ch) {
        // 4% carrier loss for a grounded contact. A common DC offset is
        // intentionally different from the reference and must cancel out.
        const bool touched = ch < 3 && (mask & (1u << ch));
        frame.adc[ch] = static_cast<std::uint16_t>(
            high ? (touched ? 2950 : 3072) : (touched ? 984 : 1024));
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
    assert(presses == 3 && releases == 3 && open_in_gap);

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
        if (fault == 0) broken.time_us += 500;
        if (fault == 1) broken.excitation_high = false;
        if (fault == 2) broken.adc[0] = 4095;
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
    std::cout << "Touch decoder: timing, three-channel events, startup and fault tests passed\n";
}
