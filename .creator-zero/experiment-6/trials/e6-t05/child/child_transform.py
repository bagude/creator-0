"""Legacy date migration per inputs/migrate.md.

Legacy strings have the form M/D/YY or M/D/YYYY (month and day one or two
digits). Output is ISO YYYY-MM-DD.
"""


def transform(s):
    """Convert a legacy date string (M/D/YY or M/D/YYYY) to ISO YYYY-MM-DD.

    - Month and day are zero-padded to two digits.
    - Two-digit years: 70-99 -> 19xx, 00-69 -> 20xx.
    - Four-digit years are used as-is.
    """
    month, day, year = s.split("/")

    if len(year) == 2:
        # NOTE: century mapping exactly as specified: 70-99 -> 19xx, 00-69 -> 20xx.
        year = ("19" if int(year) >= 70 else "20") + year
    # NOTE: the spec only defines two-digit and four-digit years; any other
    # length is used as-is (literal reading of "four-digit years are used
    # as-is" with no other case specified).

    return "{}-{}-{}".format(year, month.zfill(2), day.zfill(2))
