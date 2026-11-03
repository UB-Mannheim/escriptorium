CAN_TRAIN = 'core.can_train'


def user_can_train(user):
    """Whether `user` is allowed to launch model training (superusers always are)."""
    return bool(user and user.is_authenticated and user.has_perm(CAN_TRAIN))
