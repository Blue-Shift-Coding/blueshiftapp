from datetime import datetime

def int_to_ordinal(val):
    """
    The general rule is that, apart from teens (which are always "th") any
    numbers ending with 1, 2 or 3 have a suffix of "st", "nd" or "rd"
    respectively.
    """

    # Can't deal with floats or decimal numbers
    if val != int(val):
        raise TypeError('Cannot convert to integer')

    val = str(val)

    if len(val) >= 2 and val[-2] == '1':
        # 11th, 12th, 111th, 212th
        suffix = 'th'
    elif val[-1] == '1':
        # 1st, 21st, 31st, etc.
        suffix = 'st'
    elif val[-1] == '2':
        # 2nd, 22nd, 32nd, etc.
        suffix = 'nd'
    elif val[-1] == '3':
        # 3rd, 23rd, 33rd, etc.
        suffix = 'rd'
    else:
        suffix = 'th'

    return "{}{}".format(val, suffix)


def format_date_long(dt, include_weekday=False, include_year=False):

    if include_weekday and include_year:
        # Monday, 10th January 2020
        text = u"{weekday}, {day_of_month} {month} {year}"
    elif include_weekday:
        # Monday, 10th January
        text = u"{weekday}, {day_of_month} {month}"
    elif include_year:
        # 10th January 2020
        text = u"{day_of_month} {month} {year}"
    else:
        # 10th January
        text = u"{day_of_month} {month}"

    return text.format(
        weekday=dt.strftime('%A'),
        day_of_month=int_to_ordinal(dt.day),
        month=dt.strftime('%B'),
        year=dt.strftime('%Y'),
    )

def post_format_date(post_date):
    dt = datetime.strptime(post_date, "%Y-%m-%dT%H:%M:%S")
    return format_date_long(dt, include_year=True)
