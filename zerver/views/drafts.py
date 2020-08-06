from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse

from zerver.lib.drafts import (
    do_create_drafts,
    do_delete_draft,
    do_edit_draft,
    draft_dict_validator,
    draft_endpoint,
)
from zerver.lib.exceptions import JsonableError
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.validator import check_list
from zerver.models import Draft, UserProfile


@draft_endpoint
def fetch_drafts(request: HttpRequest, user_profile: UserProfile) -> HttpResponse:
    user_drafts = Draft.objects.filter(user_profile=user_profile).order_by("last_edit_time")
    draft_dicts = [draft.to_dict() for draft in user_drafts]
    return json_success({"count": user_drafts.count(), "drafts": draft_dicts})

@draft_endpoint
@has_request_variables
def create_drafts(request: HttpRequest, user_profile: UserProfile,
                  draft_dicts: List[Dict[str, Any]]=REQ("drafts",
                                                        validator=check_list(draft_dict_validator)),
                  ) -> HttpResponse:
    created_draft_objects = do_create_drafts(draft_dicts, user_profile)
    draft_ids = [draft_object.id for draft_object in created_draft_objects]
    return json_success({"ids": draft_ids})

@draft_endpoint
@has_request_variables
def edit_draft(request: HttpRequest, user_profile: UserProfile, draft_id: int,
               draft_dict: Dict[str, Any]=REQ("draft", validator=draft_dict_validator),
               ) -> HttpResponse:
    try:
        do_edit_draft(draft_id, draft_dict, user_profile)
    except JsonableError as err:
        return json_error(str(err), status=404)
    return json_success()

@draft_endpoint
def delete_draft(request: HttpRequest, user_profile: UserProfile, draft_id: int) -> HttpResponse:
    try:
        do_delete_draft(draft_id, user_profile)
    except JsonableError as err:
        return json_error(str(err), status=404)

    return json_success()
