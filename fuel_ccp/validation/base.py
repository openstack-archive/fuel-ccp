def validate_components_names(components, components_map):
    """Validate that requested components match existing ones."""
    valid_components = set(components_map.keys())
    invalid_components = components - valid_components
    if invalid_components:
        raise RuntimeError('Following components do not match any '
                           'definitions: %s' % ' '.join(invalid_components))
