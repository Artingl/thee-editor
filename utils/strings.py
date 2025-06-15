import string


def is_allowed_nonalpha_chars(chars, additional=""):
    allowed_chars = string.punctuation + string.digits + " "
    return all(i in allowed_chars for i in chars)


def is_allowed_alpha_chars(chars, additional=""):
    allowed_chars = string.ascii_letters + string.digits + "_" + additional
    return all(i in allowed_chars for i in chars)
