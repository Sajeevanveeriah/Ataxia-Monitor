import struct

import numpy as np
import pytest

from vw_mtc1.ltraw import RawRead, parse_meas, resample, tavg, window


def raw_file(tmp_path, *, flags="real", encoding="latin-1", newline="\n",
             values=None, binary=True, declared_points=None):
    values = np.asarray(values if values is not None else [[0, 3], [1, 4], [2, 5]])
    complex_data = "complex" in flags
    header = newline.join([
        "Title: synthetic fixture", "Plotname: AC Analysis" if complex_data else "Plotname: Transient Analysis",
        "Flags: " + flags, "No. Variables: 2",
        "No. Points: " + str(len(values) if declared_points is None else declared_points),
        "Variables:", "\t0\tfrequency\tfrequency" if complex_data else "\t0\ttime\ttime",
        "\t1\tV(out)\tvoltage", "Binary:" if binary else "Values:", "",
    ]).encode(encoding)
    if binary:
        if complex_data:
            data = values.T if "fastaccess" in flags else values
            body = np.asarray(data, dtype="<c16").tobytes()
        elif "fastaccess" in flags:
            body = values[:, 0].astype("<f8").tobytes()
            body += values[:, 1].astype("<f8" if "double" in flags else "<f4").tobytes()
        elif "double" in flags:
            body = values.astype("<f8").tobytes()
        else:
            body = b"".join(struct.pack("<df", *row) for row in values)
    else:
        def number(x):
            return f"{complex(x).real},{complex(x).imag}" if complex_data else str(x)
        body = newline.join(f"{i}\t{number(row[0])}\n\t{number(row[1])}" for i, row in enumerate(values))
        # The BOM belongs to the header, not to the data section.
        body = body.encode("utf-16-le" if encoding == "utf-16" else encoding)
    path = tmp_path / "fixture.raw"
    path.write_bytes(header + body)
    return path


@pytest.mark.parametrize("flags", ["real", "real double", "real fastaccess", "real double fastaccess"])
@pytest.mark.parametrize("encoding,newline", [("latin-1", "\n"), ("utf-16-le", "\r\n"), ("utf-16", "\n"), ("utf-8-sig", "\n")])
def test_real_binary_layouts(tmp_path, flags, encoding, newline):
    raw = RawRead(raw_file(tmp_path, flags=flags, encoding=encoding, newline=newline))
    np.testing.assert_allclose(raw["TIME"], [0, 1, 2])
    np.testing.assert_allclose(raw["v(OUT)"], [3, 4, 5])
    assert raw.has("V(out)") and not raw.has("missing")
    with pytest.raises(KeyError):
        raw["missing"]


@pytest.mark.parametrize("flags", ["complex", "complex fastaccess"])
@pytest.mark.parametrize("binary", [True, False])
def test_complex_values(tmp_path, flags, binary):
    values = [[10 + 0j, 1 + 2j], [100 + 0j, -3 - 4j]]
    raw = RawRead(raw_file(tmp_path, flags=flags, values=values, binary=binary))
    np.testing.assert_allclose(raw["V(out)"], [1 + 2j, -3 - 4j])


@pytest.mark.parametrize("binary", [True, False])
def test_negative_time_flags_do_not_create_false_steps(tmp_path, binary):
    values = [[0, 0], [-1, 1], [-2, 2], [0, 3], [-1, 4]]
    raw = RawRead(raw_file(tmp_path, flags="real stepped", values=values, binary=binary))
    np.testing.assert_allclose(raw["time"], [0, 1, 2, 0, 1])
    assert raw.step_slices() == [slice(0, 3), slice(3, 5)]


def test_missing_marker_accepts_path_objects(tmp_path):
    path = tmp_path / "bad.raw"
    path.write_bytes(b"not a waveform")
    with pytest.raises(ValueError, match="marker"):
        RawRead(path)


@pytest.mark.parametrize("flags,binary", [("real", True), ("real fastaccess", True), ("real", False)])
def test_truncated_waveforms_are_rejected(tmp_path, flags, binary):
    with pytest.raises(ValueError):
        RawRead(raw_file(tmp_path, flags=flags, binary=binary, declared_points=4))


def test_time_average_interpolates_window_boundaries():
    assert tavg(np.array([0., 1., 2., 3.]), np.array([0., 1., 4., 9.]), .5, 2.5) == pytest.approx(2.75)


def test_time_average_window_between_samples():
    assert tavg(np.array([0., 1.]), np.array([0., 1.]), .25, .75) == pytest.approx(.5)


@pytest.mark.parametrize("t0,t1", [(1, 1), (2, 1), (-1, 1), (0, 3)])
def test_time_average_rejects_invalid_window(t0, t1):
    with pytest.raises(ValueError):
        tavg(np.array([0., 1., 2.]), np.array([2., 2., 2.]), t0, t1)


def test_resample_and_window():
    t, y = resample(np.array([0., 1., 2.]), np.array([0., 2., 4.]), .5)
    np.testing.assert_allclose(t, [0, .5, 1, 1.5])
    np.testing.assert_allclose(y, [0, 1, 2, 3])
    tt, yy = window(t, y, .5, 1.)
    np.testing.assert_allclose(tt, [.5, 1.])
    np.testing.assert_allclose(yy, [1, 2])


@pytest.mark.parametrize("encoding", ["latin-1", "utf-16-le", "utf-16"])
def test_measurement_encodings_and_timing(tmp_path, encoding):
    path = tmp_path / "test.log"
    path.write_bytes(("vavg: AVG(V(out))=3.3 FROM 0 TO 1\r\n"
                      "t90: V(out)=2.97 AT 0.001\r\n"
                      "gain=-2.5e-3\r\nMeasurement \"missing\" FAIL'ed\r\n").encode(encoding))
    results = parse_meas(path)
    assert results == {"vavg": 3.3, "t90": .001, "gain": -.0025}
