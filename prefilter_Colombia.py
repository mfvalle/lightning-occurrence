import pandas as pd
from pathlib import Path

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
INPUT_FILE  = "A20260121.loc"            # your input file
OUTPUT_FILE = "preFilter_A20260121.loc"   # output file
CHUNK_SIZE  = 500000                   # adjust depending on memory

# Colombia bounding box
LON_MIN, LON_MAX = -79.1, -66.85
LAT_MIN, LAT_MAX =  -4.5,  13.6

# Column names based on your sample
col_names = ["date", "time", "lat", "lon", "energy", "nsta"]

# ---------------------------------------------------------
# PREPARE OUTPUT (clean file)
# ---------------------------------------------------------
Path(OUTPUT_FILE).write_text("")  # truncate file if exists

# ---------------------------------------------------------
# READ THE .loc IN CHUNKS
# ---------------------------------------------------------
chunk_iter = pd.read_csv(
    INPUT_FILE,
    sep=",",
    skipinitialspace=True,
    header=None,
    names=col_names,
    dtype={
        "date": "string",
        "time": "string",
        "lat": "float64",
        "lon": "float64",
        "energy": "float64",
        "nsta": "int64"
    },
    engine="python",
    chunksize=CHUNK_SIZE
)

total_kept = 0

# ---------------------------------------------------------
# PROCESS CHUNKS
# ---------------------------------------------------------
for i, chunk in enumerate(chunk_iter, start=1):

    # Coordinate sanity
    chunk = chunk[
        chunk["lat"].between(-90, 90) &
        chunk["lon"].between(-180, 180)
    ]

    # Bounding box filter
    mask = (
        (chunk["lon"] >= LON_MIN) & (chunk["lon"] <= LON_MAX) &
        (chunk["lat"] >= LAT_MIN) & (chunk["lat"] <= LAT_MAX)
    )
    filtered = chunk.loc[mask, col_names]

    # Write to output (append mode)
    filtered.to_csv(
        OUTPUT_FILE,
        index=False,
        header=False,
        mode="a"
    )

    total_kept += len(filtered)
    print(f"Chunk {i}: kept {len(filtered)} rows (total so far: {total_kept})")

# ---------------------------------------------------------
# DONE
# ---------------------------------------------------------
print("\nFinished!")
print(f"Total strokes inside Colombia BBOX: {total_kept}")
print(f"Output saved to: {OUTPUT_FILE}")
