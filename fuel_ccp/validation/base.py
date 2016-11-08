from fuel_ccp import config

CONF = config.CONF


def require_config_sections(sections=None):
    """Decorator to validate that configs contains command-specific sections"""
    sections = sections or []

    def validate_required():
        missing_sections = []
        for section in sections:
            try:
                if not CONF[section]._dict:
                    missing_sections.append(section)
            except KeyError:
                missing_sections.append(section)
        if missing_sections:
            raise RuntimeError(
                "The following sections: %s aren't specified in "
                "configs" % ', '.join(missing_sections))

    return validate_required


def validate_components_names(components, components_map):
    """Validate that requested components match existing ones."""
    valid_components = set(components_map.keys())
    invalid_components = components - valid_components
    if invalid_components:
        raise RuntimeError('Following components do not match any '
                           'definitions: %s' % ' '.join(invalid_components))
