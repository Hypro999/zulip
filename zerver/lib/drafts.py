import time
from functools import wraps
from typing import Any, Dict, List, Set, cast

from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.utils.translation import ugettext as _

from zerver.lib.actions import recipient_for_user_profiles
from zerver.lib.addressee import get_user_profiles_by_ids
from zerver.lib.exceptions import JsonableError
from zerver.lib.message import truncate_body, truncate_topic
from zerver.lib.streams import access_stream_by_id
from zerver.lib.timestamp import timestamp_to_datetime
from zerver.lib.types import ViewFuncT
from zerver.lib.validator import (
    check_dict_only,
    check_float,
    check_int,
    check_list,
    check_required_string,
    check_string,
    check_string_in,
    check_union,
)
from zerver.models import Draft, UserProfile

VALID_DRAFT_TYPES: Set[str] = {"", "private", "stream"}

# A validator to verify if the structure (syntax) of a dictionary
# meets the requirements to be a draft dictionary:
draft_dict_validator = check_dict_only(
    required_keys=[
        ("type", check_string_in(VALID_DRAFT_TYPES)),
        ("to", check_list(check_int)),  # The ID of the stream to send to, or a list of user IDs.
        ("topic", check_string),  # This string can simply be empty for private type messages.
        ("content", check_required_string),
    ],
    optional_keys=[
        ("timestamp", check_union([check_int, check_float])),  # A Unix timestamp.
    ]
)

def further_validated_draft_dict(draft_dict: Dict[str, Any],
                                 user_profile: UserProfile) -> Dict[str, Any]:
    """ Take a draft_dict that was already validated by draft_dict_validator then
    further sanitize, validate, and transform it. Ultimately return this "further
    validated" draft dict. It will have a slightly different set of keys the values
    for which can be used to directly create a Draft object. """

    content = truncate_body(draft_dict["content"])
    if "\x00" in content:
        raise JsonableError(_("Content must not contain null bytes"))

    timestamp = draft_dict.get("timestamp", time.time())
    timestamp = round(timestamp, 6)
    if timestamp < 0:
        # While it's not exactly an invalid timestamp, it's not something
        # we want to allow either.
        raise JsonableError(_("Timestamp must not be negative."))
    last_edit_time = timestamp_to_datetime(timestamp)

    topic = ""
    recipient = None
    to = draft_dict["to"]
    if draft_dict["type"] == "stream":
        topic = truncate_topic(draft_dict["topic"])
        if "\x00" in topic:
            raise JsonableError(_("Topic must not contain null bytes"))
        if len(to) != 1:
            raise JsonableError(_("Must specify exactly 1 stream ID for stream messages"))
        stream, sub = access_stream_by_id(user_profile, to[0])
        recipient = stream.recipient
    elif draft_dict["type"] == "private" and len(to) != 0:
        to_users = get_user_profiles_by_ids(set(to), user_profile.realm)
        try:
            recipient = recipient_for_user_profiles(to_users, False, None, user_profile)
        except ValidationError as e:  # nocoverage
            raise JsonableError(e.messages[0])

    return {
        "recipient": recipient,
        "topic": topic,
        "content": content,
        "last_edit_time": last_edit_time,
    }

def draft_endpoint(view_func: ViewFuncT) -> ViewFuncT:
    @wraps(view_func)
    def draft_view_func(request: HttpRequest, user_profile: UserProfile,
                        *args: object, **kwargs: object) -> HttpResponse:
        if not user_profile.enable_drafts_synchronization:
            raise JsonableError(_("User has not enabled drafts syncing."))
        return view_func(request, user_profile, *args, **kwargs)
    return cast(ViewFuncT, draft_view_func)  # https://github.com/python/mypy/issues/1927

def do_create_drafts(draft_dicts: List[Dict[str, Any]], user_profile: UserProfile) -> List[Draft]:
    """ Create drafts in bulk for a given user based on the draft dicts. Since
    currently, the only place this method is being used (apart from tests) is from
    the create_draft view, we assume that the drafts_dicts are syntactically valid
    (i.e. they satisfy the draft_dict_validator). """
    draft_objects = []
    for draft_dict in draft_dicts:
        valid_draft_dict = further_validated_draft_dict(draft_dict, user_profile)
        draft_objects.append(Draft(
            user_profile=user_profile,
            recipient=valid_draft_dict["recipient"],
            topic=valid_draft_dict["topic"],
            content=valid_draft_dict["content"],
            last_edit_time=valid_draft_dict["last_edit_time"],
        ))

    created_draft_objects = Draft.objects.bulk_create(draft_objects)
    return created_draft_objects

def do_edit_draft(draft_id: int, draft_dict: Dict[str, Any], user_profile: UserProfile) -> None:
    """ Edit/update a single draft for a given user. Since the only place this method is being
    used from (apart from tests) is the edit_draft view, we assume that the drafts_dict is
    syntactically valid (i.e. it satisfies the draft_dict_validator). """
    try:
        draft_object = Draft.objects.get(id=draft_id, user_profile=user_profile)
    except Draft.DoesNotExist:
        raise JsonableError(_("Draft does not exist"))

    valid_draft_dict = further_validated_draft_dict(draft_dict, user_profile)
    draft_object.content = valid_draft_dict["content"]
    draft_object.topic = valid_draft_dict["topic"]
    draft_object.recipient = valid_draft_dict["recipient"]
    draft_object.last_edit_time = valid_draft_dict["last_edit_time"]
    draft_object.save()
    return

def do_delete_draft(draft_id: int, user_profile: UserProfile) -> None:
    """ Delete a draft belonging to a particular user. """
    try:
        draft_object = Draft.objects.get(id=draft_id, user_profile=user_profile)
    except Draft.DoesNotExist:
        raise JsonableError(_("Draft does not exist"))

    draft_object.delete()
    return

def do_enable_drafts_syncing(user_profile: UserProfile) -> None:
    """ Set the user's enable_drafts_synchronization field to True """
    user_profile.enable_drafts_synchronization = True
    user_profile.save(update_fields=["enable_drafts_synchronization"])
    return

def do_disable_drafts_syncing(user_profile: UserProfile) -> None:
    """ Set the user's enable_drafts_synchronization field to False and delete
    all of their currently synced drafts from the backend. """
    user_profile.enable_drafts_synchronization = False
    user_profile.save(update_fields=["enable_drafts_synchronization"])
    Draft.objects.filter(user_profile=user_profile).delete()
    return
