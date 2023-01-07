// Copyright (c) Meta Platforms, Inc. and affiliates.
// All rights reserved.
//
// This source code is licensed under the BSD-style license found in the
// LICENSE file in the root directory of this source tree.

#include "fairseq2/native/data/text/detail/utf.h"

#include <cstdint>

#include "fairseq2/native/span.h"

namespace fairseq2 {
namespace detail {

std::size_t
compute_code_point_length(std::string_view s)
{
    std::size_t len = 0;

    for (auto iter = s.begin(); iter < s.end();) {
        std::size_t size = 0;

        auto lead = static_cast<std::uint8_t>(*iter);
             if ((lead & 0x80) == 0x00)
            size = 1;
        else if ((lead & 0xe0) == 0xc0)
            size = 2;
        else if ((lead & 0xf0) == 0xe0)
            size = 3;
        else if ((lead & 0xf8) == 0xf0)
            size = 4;

        if (size == 0 || static_cast<std::size_t>(s.end() - iter) < size)
            throw invalid_utf8_error{"The specified string has an invalid UTF-8 code point."};

        iter += size;

        len++;
    }

    return len;
}

std::string
infer_bom_encoding(memory_span preamble) noexcept
{
    auto chars = cast<const unsigned char>(preamble);

    if (chars.size() >= 3)
        if (chars[0] == 0xef && chars[1] == 0xbb && chars[2] == 0xbf)
            return "UTF-8";

    if (chars.size() >= 4) {
        if (chars[0] == 0x00 && chars[1] == 0x00 && chars[2] == 0xfe && chars[3] == 0xff)
            return "UTF-32BE";

        if (chars[0] == 0xff && chars[1] == 0xfe && chars[2] == 0x00 && chars[3] == 0x00)
            return "UTF-32LE";
    }

    if (chars.size() >= 2) {
        if (chars[0] == 0xfe && chars[1] == 0xff)
            return "UTF-16BE";

        if (chars[0] == 0xff && chars[1] == 0xfe)
            return "UTF-16LE";
    }

    return "UTF-8";
}

}  // namespace detail

invalid_utf8_error::~invalid_utf8_error() = default;

}  // namespace fairseq2