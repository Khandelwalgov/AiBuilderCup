"""One typed personal discovery result; trust states and publication gates stay distinct."""

from opportunity_platform.retrieval.service import (
    SearchRequest,
    SearchResponse,
    SearchSubject,
    search,
)
from opportunity_platform.subjects.service import SubjectRef, resolve, subject_facts, view

from .guidance import GuidanceRequest, GuidanceResponse, guidance, with_overrides


class DiscoveryResponse(GuidanceResponse):
    reviewed: SearchResponse


def discover(session, uid, request: GuidanceRequest):
    hypothetical = request.scenario or bool(request.overrides) or bool(request.member_overrides)
    ref = request.subject
    _, obj, _ = resolve(session, uid, ref, read_only=True)
    objects = [(ref.kind, obj)]
    if ref.kind == "household":
        for member in view(session, uid, ref, read_only=True).members:
            if member.get("access") == "authorized":
                _, person, _ = resolve(session, uid, SubjectRef(id=member["id"]), read_only=True)
                objects.append(("person", person))
    subjects = [
        SearchSubject(
            f"{kind}:{person.id}",
            kind,
            getattr(person, "display_name", getattr(person, "name", kind)),
            person.id,
            with_overrides(
                subject_facts(session, kind, person.id),
                request.overrides
                if person.id == obj.id
                else request.member_overrides.get(f"{kind}:{person.id}", []),
            ),
            hypothetical,
        )
        for kind, person in objects
        if f"{kind}:{person.id}" not in request.excluded_subject_keys
    ]
    subjects += [
        SearchSubject(
            "scenario:person:" + person.key,
            "person",
            "Hypothetical · " + person.name,
            None,
            with_overrides([], person.facts),
            True,
        )
        for person in request.people
    ]
    reviewed = search(
        session,
        uid,
        SearchRequest(
            mode={"person": "me", "household": "family", "business": "business"}[ref.kind],
            subject_id=obj.id,
            q=request.q,
            category=request.category or None,
        ),
        subjects=subjects,
    )
    # Explicit canonical programme mappings, never broad title-similarity/source-PDF dedupe.
    canonical = {
        "1ed2eea7-7a4e-5681-83e8-97807e802dd6": "msme-team",
        "a4b79e71-439d-5ea7-be65-22dad5dd765e": "post-matric-st",
    }
    represented = {canonical.get(str(item.opportunity.id)) for item in reviewed.items}
    result = guidance(session, uid, request, exclude_parents=represented)
    if result.hypothetical:
        from opportunity_platform.planning.service import research_actions

        result.actions = research_actions(session, uid, request, persist=False)
    return DiscoveryResponse(**result.model_dump(), reviewed=reviewed)
