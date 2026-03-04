from doepy import build

def buildCC(bounds, variables):

    DoE_dict = {}
    for variable, bound in zip(variables, bounds):
        new_dict_item = {variable : bound}
        DoE_dict = {**DoE_dict, **new_dict_item}

    design = build.central_composite(
        DoE_dict,
        center=(1, 1),
        alpha='orthogonal',
        face='cci'
    )

    return design


#legacy code, used in method builder, untouched by Zak - unsure of impact on other files, so not deleted.