# returns the following day
def next(day):
    if day == "SUN":
        return "MON"
    elif day == "MON":
        return "TUE"
    elif day == "TUE":
        return "WED"
    elif day == "WED":
        return "THU"
    elif day == "THU":
        return "FRI"
    elif day == "FRI":
        return "SAT"
    elif day == "SAT":
        return "SUN"
    else:
        return "invalid entry"


# returns the previous day
def previous(day):
    if day == "SUN":
        return "SAT"
    elif day == "MON":
        return "SUN"
    elif day == "TUE":
        return "MON"
    elif day == "WED":
        return "TUE"
    elif day == "THU":
        return "WED"
    elif day == "FRI":
        return "THU"
    elif day == "SAT":
        return "FRI"
    else:
        return "invalid entry"