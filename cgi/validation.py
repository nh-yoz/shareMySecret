#!/bin/python3
# Module Validation

import datetime, re
from typing import Union


def is_str(value) -> bool:
    try:
        return type(value) is str
    except:
        return False


def is_int(value) -> bool:
    try:
        return type(value) is int
    except:
        return False


def is_float(value) -> bool:
    try:
        return type(value) is float
    except:
        return False


def is_bool(value) -> bool:
    try:
        return type(value) is bool or (type(value) is int and value in [0, 1])
    except:
        return False


def is_number(value) -> bool:
    return is_float(value) or is_int(value) 


def is_none(value) -> bool:
    return value is None


def is_dict(value) -> bool:
    try:
        return type(value) is dict
    except:
        return False


def is_tuple(value) -> bool:
    try:
        return type(value) is tuple
    except:
        return False


def is_list(value) -> bool:
    try:
        return type(value) is list
    except:
        return False
    
def is_array(value) -> bool:
    return is_list(value) or is_tuple(value)


def is_isodatetime(value) -> bool:
    if not is_str(value):
        return False
    try:
        test = datetime.datetime.fromisoformat(value)
        return True
    except:
        return False


def is_oneof(value: Union[str, int, float], values: list) -> bool:
    for v in values:
        if value == v:
            return True
    return False


def is_noneof(value: Union[str, int, float], values: list) -> bool:
    for v in values:
        if value == v:
            return False
    return True



def is_exactly(value, rule_value) -> bool:
    return value == rule_value


def is_cron(value: str) -> bool:
    # ┌───────────── minute (0 - 59)
    # │ ┌───────────── hour (0 - 23)
    # │ │ ┌───────────── day of the month (1 - 31)
    # │ │ │ ┌───────────── month (1 - 12)
    # │ │ │ │ ┌───────────── day of the week (0 - 6) (Sunday to Saturday)
    # │ │ │ │ │
    # * * * * *
    if not is_str(value):
        return False
    if re.match('^[0-9*]*$', re.sub('[ ,-]', '', value)) is None:
        return False
    arr = value.split(' ')
    if len(arr) != 5:
        return False
    def to_num_arr(string: str) -> list:
        ret_arr = []
        for s_1 in string.split(','):
            s_2 = s_1.split('-')
            if len(s_2) > 2:
                return None
            for string in s_2:
                if not string.isdigit():
                    return None
            if len(s_2) == 2:
                a = int(s_2[0])
                b = int(s_2[1])
                if a > b:
                    return None
                ret_arr.extend(range(a, b + 1))
            else:
                 ret_arr.append(int(s_2[0]))
        return ret_arr
    ranges = [ range(0, 60), range(0, 24), range(1, 32), range(1, 13), range(0, 7) ]
    for i in range(0, 5):
        if arr[i] != '*':
            test_arr = to_num_arr(arr[i])
            if test_arr is None:
                return False
            if not all(int(item) in ranges[i] for item in test_arr):
                return False
    return True


def is_regex(value: str, regex: str) -> bool:
    if not is_str(value):
        return False
    return re.search(regex, value) != None


def is_email(value: str) -> bool:
    if not is_str(value):
        return False
    email_regex = re.compile(r'^([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+$')
    return email_regex.fullmatch(value) is not None

def is_url(value: str) -> bool:
    if not is_str(value):
        return False
    url_regex = re.compile(r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$')
    return url_regex.fullmatch(value) is not None


def is_minmax(value: Union[str, int, float, list, tuple], min_max_exp: str) -> bool: # min_max_exp = ]4,5]
    if is_number(value):
        l = value
    elif is_str(value) or is_list(value) or is_tuple(value):
        l = len(value)
    else:
        return False
    bounderies = min_max_exp.split(',')
    if len(bounderies[0]) > 1:
        min = bounderies[0][1:]
        min = float(min) if '.' in min else int(min)
        if bounderies[0][0] == '[':
            if l < min:
                return False
        else:
            if l <= min:
                return False
    if len(bounderies[1]) > 1:
        max = bounderies[1][:-1]
        max = float(max) if '.' in max else int(max)
        if bounderies[1][-1:] == ']':
            if l > max:
                return False
        else:
            if l >= max:
                return False
    return True

def is_min(value: Union[str, int, float, list, tuple], min: int) -> bool: 
    if is_number(value):
        l = value
    elif is_str(value) or is_list(value) or is_tuple(value):
        l = len(value)
    else:
        return False
    if l < min:
        return False
    return True

def is_max(value: Union[str, int, float, list, tuple], max: int) -> bool: 
    if is_number(value):
        l = value
    elif is_str(value) or is_list(value) or is_tuple(value):
        l = len(value)
    else:
        return False
    if l > max:
        return False
    return True

type_functions = {
    "str": is_str,
    "int": is_int,
    "float": is_float,
    "number": is_number,
    "bool": is_bool,
    "dict": is_dict,
    "tuple": is_tuple,
    "list": is_list,
    "none": is_none,
}

special_functions = {
    "email": is_email,
    "url": is_url,
    "cron": is_cron,
    "isodatetime": is_isodatetime
}

def validate_value(key: str, value, constraint: Union[str, list, tuple]) -> str:
    if is_array(constraint) and is_array(constraint[0]):
        return validate_value(key, value, constraint[0])
    if constraint[0] == 'and':
        for c in constraint[1]:
            res = validate_value(key, value, c)
            if res != '':
                return res
    elif constraint[0] == 'or':
        errors = []
        for c in constraint[1]:
            res = validate_value(key, value, c)
            errors.append(res)
        if all(errors):
            return errors[0]
        else:
            return ''
    else:
        retval = ''
        if is_str(constraint):
            constraint_local = [constraint]
        else:
            constraint_local = constraint
        name = constraint_local[0]
        if name == 'any':
            return retval
        if len(constraint_local) == 1:
            if name in type_functions.keys():
                if not type_functions[name](value):
                    retval = f'Type invalid for {key}. Should be {name}.'
            elif name in special_functions.keys():
                if not special_functions[name](value):
                    retval = f'{key} is invalid. Should be a valid {name}.'
            else:
                retval =  f'Invalid validation rule name: {name}.'
        elif len(constraint_local) == 2:
            rule = constraint_local[1]
            if name == 'type':
                if not type_functions[rule](value):
                    retval = f'Type invalid for {key}. Should be {rule}.'
            elif name == 'minmax':
                if not is_minmax(value, rule):
                    retval = f'{key} is out of bounds. Should be {rule}.'
            elif name == 'min':
                if not is_min(value, rule):
                    retval = f'{key} is out of bounds. Should be greater or equal to {rule}.'
            elif name == 'max':
                if not is_max(value, rule):
                    retval = f'{key} is out of bounds. Should be lower or equal to {rule}.'
            elif name == 'noneof':
                if not is_noneof(value, rule):
                    retval = f'{key} is invalid. Should be none of {rule}.'
            elif name == 'oneof':
                if not is_oneof(value, rule):
                    retval = f'{key} is invalid. Should be one of {rule}.'
            elif name == 'regexp':
                if not is_regex(value, rule):
                    retval = f'{key} is invalid. Should compare to this regular expression: {rule}.'
            elif name == 'is':
                if not is_exactly(value, rule):
                    retval = f'{key} is invalid. Should be = {rule}.'
            else:
                retval =  f'Invalid validation rule name: {name}.'
        else:
            retval =  f'Invalid validation rule name: {name}.'
        return retval


def validate_dict(dict_to_validate: dict, validation_dict: dict):
    # validation_dict = {
    #     'any_key': ['and', [('type', 'str'), ('minmax', '[4,8]')], -> string of length 4, 5, 6, 7 or 8
    #     'age': ['and', (('type', 'int'), ('minmax', '[4,5['))],
    #     'name': ['and', (('type', 'str'), ('minmax', '[3, 20]'), ('regexp', '^[a-zA-Z]* [a-zA-Z]*'))],
    #     'key_4': ['optional', 'and', (('type', "str"), ('minmax', '[4,5]'))]
    # }
    # Format: { key -> rule[] } where rule is a tuple or list: (rule_name: str, rule: str).
    # The constraints will be evaluated in order
    for key in dict_to_validate:
        if not key in validation_dict:
            raise Exception(f'Invalid key: {key}')
    for key in validation_dict:
        constraints = validation_dict[key]
        if not key in dict_to_validate and not 'optional' in (constraints, constraints[0]):
            raise Exception(f'Missing key: {key}')
    for key in dict_to_validate:
        constraints = validation_dict[key]
        if constraints[0] == 'optional':
            constraints = list(constraints)
            constraints.pop(0)
        res = validate_value(key, dict_to_validate[key], constraints)
        if res:
            raise Exception(res)
