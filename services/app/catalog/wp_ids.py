"""WordPress user id -> UUID. The auth service uses the result as the user's pk and the main app
as the reviewer's pk, which is how the two link with no runtime call (A3). The rule is the
contract docs/contracts/auth/reviewer-ids.json; a test in each service checks it."""

import uuid

WP_USER_NAMESPACE = uuid.UUID("b88cc69f-2c32-5407-a15f-e0e254c8057a")


def wp_user_uuid(wp_user_id: int) -> uuid.UUID:
    return uuid.uuid5(WP_USER_NAMESPACE, str(wp_user_id))
