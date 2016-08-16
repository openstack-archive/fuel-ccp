def validate_components_names(components, components_map):
    valid_components = set(components_map.keys())
    invalid_components = components - valid_components
    if invalid_components:
        raise RuntimeError('Following components do not match any '
                           'definition: %s' % ' '.join(invalid_components))
