#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sort a CSV-like WWLLN .loc file by timestamp:
  date = YYYY/MM/DD
  time = HH:MM:SS.ffffff (microseconds; any fractional length tolerated)

- Keeps header/comment/blank lines (%, #, empty) at the top, verbatim.
- Writes data lines back verbatim (no reformatting).
- Stable sort by (Y, M, D, h, m, s, microseconds) using integer tuple (no floats).

Usage:
    python sort_wwlln_loc_csv.py input.loc
    python sort_wwlln_loc_csv.py input.loc output_sorted.loc
"""

import sys
import os
import re

HEADER_PREFIXES = ('%', '#')

def is_header_line(line: str) -> bool:
    s = line.lstrip()
    return (not s) or s.startswith(HEADER_PREFIXES)

def parse_datetime_key_csv(line: str):
    """
    Expect first two comma-separated fields:
      tokens[0] = 'YYYY/MM/DD' (also tolerates YYYY-MM-DD or YYYY MM DD)
      tokens[1] = 'HH:MM:SS(.fraction)'
    Return (Y, M, D, h, m, s, usec) or None if unparseable.
    """
    # Split CSV; tolerate spaces around commas
    tokens = [t.strip() for t in line.strip().split(',')]
    if len(tokens) < 2:
        return None

    date_str = tokens[0]
    time_str = tokens[1]

    # Parse date
    dparts = re.split(r'[/\-\s]+', date_str)
    if len(dparts) != 3:
        return None
    try:
        Y = int(dparts[0])
        M = int(dparts[1])
        D = int(dparts[2])
    except Exception:
        return None

    # Parse time HH:MM:SS(.fraction)
    tparts = time_str.split(':')
    if len(tparts) != 3:
        return None
    try:
        h = int(tparts[0])
        m = int(tparts[1])

        sec_token = tparts[2]
        if '.' in sec_token:
            s_part, frac = sec_token.split('.', 1)
        else:
            s_part, frac = sec_token, ''
        s = int(s_part)

        # Normalize fraction to 6 digits (microseconds), padding/truncating as needed
        frac_digits = re.sub(r'\D', '', frac)
        frac6 = (frac_digits + '000000')[:6]  # pad then truncate to 6
        usec = int(frac6) if frac6 else 0

        # Basic sanity checks (adjust if your file can have leap seconds, etc.)
        if not (1 <= M <= 12 and 1 <= D <= 31 and 0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 60 and 0 <= usec <= 999999):
            return None

        return (Y, M, D, h, m, s, usec)
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python sort_wwlln_loc_csv.py input.loc [output.loc]", file=sys.stderr)
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) >= 3 else os.path.splitext(in_path)[0] + "_sorted.loc"

    if not os.path.isfile(in_path):
        print(f"Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    headers = []
    data = []  # list of (key, line)
    bad_count = 0

    with open(in_path, 'r', encoding='utf-8', errors='replace') as fi:
        for line in fi:
            if is_header_line(line):
                headers.append(line)
                continue
            key = parse_datetime_key_csv(line)
            if key is None:
                # Keep unparsable non-header lines at the end without losing them
                key = (9999, 12, 31, 23, 59, 60, 999999)
                bad_count += 1
            data.append((key, line))

    # Stable sort by full timestamp
    data.sort(key=lambda kv: kv[0])

    with open(out_path, 'w', encoding='utf-8') as fo:
        for h in headers:
            fo.write(h)
        for _, line in data:
            fo.write(line)

    msg = f"Sorted file written to: {out_path}"
    if bad_count:
        msg += f" (note: {bad_count} line(s) could not be parsed for timestamp and were placed at the end)"
    print(msg)

if __name__ == "__main__":
    main()
