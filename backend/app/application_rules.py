from fastapi import HTTPException, status
from typing import Protocol

from app.models import AllowedTenantType, RoomListing, TenantType


class ApplicationTenantDetails(Protocol):
    tenant_type: TenantType
    tenant_category: str | None
    tenant_subtype: str | None
    student_number: str | None
    institution: str | None
    institution_name: str | None
    occupation: str | None
    employer_or_business_name: str | None
    work_location: str | None
    number_of_occupants: int | None


def validate_application_against_listing(
    listing: RoomListing,
    payload: ApplicationTenantDetails,
) -> None:
    category = (payload.tenant_category or payload.tenant_type.value).strip().lower()
    subtype = (payload.tenant_subtype or "").strip().lower()
    is_student = category == "student"

    if (
        listing.allowed_tenant_type == AllowedTenantType.student
        and not is_student
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This room is available for student tenants only.",
        )

    if (
        listing.allowed_tenant_type == AllowedTenantType.non_student
        and is_student
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This room is available for non-student tenants only.",
        )

    if category == "student":
        if not subtype or not (payload.institution_name or payload.institution):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Student applications require subtype and institution name.",
            )

    if category == "worker" and not payload.occupation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Worker applications require occupation.",
        )

    if category == "family" and not payload.number_of_occupants:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Family applications require number of occupants.",
        )


def validate_application_record_against_listing(
    listing: RoomListing,
    tenant_type: TenantType,
    institution: str | None,
    student_number: str | None,
    occupation: str | None,
    tenant_category: str | None = None,
    tenant_subtype: str | None = None,
    institution_name: str | None = None,
    employer_or_business_name: str | None = None,
    work_location: str | None = None,
    number_of_occupants: int | None = None,
) -> None:
    class Payload:
        tenant_type: TenantType
        tenant_category: str | None
        tenant_subtype: str | None
        institution: str | None
        institution_name: str | None
        student_number: str | None
        occupation: str | None
        employer_or_business_name: str | None
        work_location: str | None
        number_of_occupants: int | None

    payload = Payload()
    payload.tenant_type = tenant_type
    payload.tenant_category = tenant_category
    payload.tenant_subtype = tenant_subtype
    payload.institution = institution
    payload.institution_name = institution_name
    payload.student_number = student_number
    payload.occupation = occupation
    payload.employer_or_business_name = employer_or_business_name
    payload.work_location = work_location
    payload.number_of_occupants = number_of_occupants

    validate_application_against_listing(listing, payload)
