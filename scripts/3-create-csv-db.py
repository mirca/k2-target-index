"""Augment and export CSV/SQLite files detailing all K2 target pixel files.
"""
import glob
import logging
import sqlite3
from tqdm import tqdm

import pandas as pd

from astropy import wcs


log = logging.getLogger(__name__)
log.setLevel("INFO")

# Output filenames
CSV_FILENAME = "../k2-target-pixel-files.csv.gz"
SQLITE_FILENAME = "../k2-target-pixel-files.db"


def create_wcs(row):
    """Returns a `astropy.wcs.WCS` instance for a target mask given its row."""
    # First we create a WCS object from the metadata
    metadata = {}
    metadata['CTYPE1'] = 'RA---TAN'
    metadata['CTYPE2'] = 'DEC--TAN'
    for kw in ['naxis1', 'naxis2', 'crpix1', 'crpix2', 'crval1', 'crval2',
               'cdelt1', 'cdelt2', 'pc1_1', 'pc1_2', 'pc2_1', 'pc2_2',
               'crval1p', 'crval2p']:
        metadata[kw] = row[kw]
    return wcs.WCS(metadata)


def mask_corners(row):
    """Returns the corners of a target mask given its target index row."""
    mywcs = create_wcs(row)
    # Then figure out the corners
    x, y = row['naxis1'], row['naxis2']  # Mask dimensions
    corners = mywcs.all_pix2world([-0.5, -0.5, x-0.5, x-0.5],
                                  [-0.5, y-0.5, y-0.5, -0.5],
                                  0)
    del mywcs
    return corners


def add_corners(df):
    """Adds corner columns to the target index dataframe."""
    col_corners, col_ra_min, col_ra_max, col_dec_min, col_dec_max = [], [], [], [], []
    for idx, row in tqdm(df.iterrows(), desc="Adding corner coordinates", total=len(df)):
        corners = mask_corners(row)
        # String serialization
        str_repr = ";".join(["{:.6f},{:.6f}".format(corners[0][idx], corners[1][idx])
                             for idx in range(len(corners[0]))])
        col_corners.append(str_repr)
        # Bounding box in equatorial coordinates
        ra_min, ra_max = corners[0].min(), corners[0].max()
        dec_min, dec_max = corners[1].min(), corners[1].max()
        col_ra_min.append("{:.6f}".format(ra_min))
        col_ra_max.append("{:.6f}".format(ra_max))
        col_dec_min.append("{:.6f}".format(dec_min))
        col_dec_max.append("{:.6f}".format(dec_max))
    df['corners'] = col_corners
    df['ra_min'] = col_ra_min
    df['ra_max'] = col_ra_max
    df['dec_min'] = col_dec_min
    df['dec_max'] = col_dec_max
    return df


if __name__ == "__main__":
    log.info("Reading the data")
    df = pd.concat([pd.read_csv(fn)
                    for fn
                    in glob.glob("intermediate-data/*metadata.csv")])
    df = df.sort_values("keplerid")
    df = add_corners(df)

    # Write to the CSV file
    log.info("Writing {}".format(CSV_FILENAME))
    df.to_csv(CSV_FILENAME, index=False, compression="gzip")

    # Write the SQLite table
    log.info("Writing {}".format(SQLITE_FILENAME))
    con = sqlite3.connect(SQLITE_FILENAME)
    df.to_sql(name='tpf', con=con, if_exists='replace', index=False)