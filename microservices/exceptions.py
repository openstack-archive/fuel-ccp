class CCPException(Exception):
    """Base Exception for the project """
    pass


class ImageBuildException(CCPException):
    def __init__(self, image, reason):
        super(CCPException, self).__init__(
            'The "%s" image build failed: "%s"' % (image, reason))


class ImagePushException(CCPException):
    def __init__(self, image, registry, reason):
        super(CCPException, self).__init__(
            'The "%s" image push to the registry "%s" failed: "%s"' % (
                image, registry, reason))
