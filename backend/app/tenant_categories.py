TENANT_CATEGORY_DETAILS: dict[str, tuple[str, ...]] = {
    "student": (
        "nul_student",
        "limkokwing_student",
        "tvet_student",
        "college_student",
        "other_student",
    ),
    "worker": (
        "employed",
        "government_worker",
        "private_company_worker",
        "self_employed",
        "remote_worker",
        "other_worker",
    ),
    "family": (
        "small_family",
        "single_parent",
        "large_family",
        "other_family",
    ),
    "business": (
        "office_staff",
        "shop_workers",
        "construction_team",
        "other_business",
    ),
    "visitor_short_stay": (
        "daily",
        "weekly",
        "monthly",
    ),
    "ngo_organization": (
        "ngo_staff",
        "church_organization",
        "project_team",
        "other_organization",
    ),
    "foreigner_international": (
        "international_student",
        "international_worker",
        "visitor",
        "other_international",
    ),
    "shared_occupancy": (
        "2_people_sharing",
        "3_people_sharing",
        "group_sharing",
    ),
    "couple": (
        "married_couple",
        "partners",
        "other_couple",
    ),
    "other": (
        "other",
    ),
}

GENDER_PREFERENCES = {"any", "male", "female"}
GENDER_NORMALIZATION = {
    "": "any",
    "any": "any",
    "both": "any",
    "all": "any",
    "everyone": "any",
    "male": "male",
    "men": "male",
    "man": "male",
    "m": "male",
    "female": "female",
    "women": "female",
    "woman": "female",
    "f": "female",
}


def normalize_slug(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower().replace("/", " ").replace("-", " ").replace(" ", "_")


def normalize_gender_preference(value: str | None) -> str:
    normalized = normalize_slug(value) or "any"
    return GENDER_NORMALIZATION.get(normalized, normalized)


def normalize_tenant_category(value: str | None) -> str | None:
    normalized = normalize_slug(value)
    if normalized == "visitor":
        return "visitor_short_stay"
    if normalized == "ngo":
        return "ngo_organization"
    if normalized == "foreigner":
        return "foreigner_international"
    return normalized


def validate_tenant_category_detail(category: str | None, detail: str | None) -> tuple[str | None, str | None]:
    normalized_category = normalize_tenant_category(category)
    normalized_detail = normalize_slug(detail)

    if not normalized_category:
        return None, normalized_detail

    if normalized_category not in TENANT_CATEGORY_DETAILS:
        raise ValueError("Tenant category is not supported.")

    allowed_details = TENANT_CATEGORY_DETAILS[normalized_category]
    if normalized_detail and normalized_detail not in allowed_details:
        raise ValueError("Category detail does not match tenant category.")

    if not normalized_detail:
        normalized_detail = allowed_details[0]

    return normalized_category, normalized_detail
