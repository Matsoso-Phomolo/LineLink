export type TenantCategory =
  | "student"
  | "worker"
  | "family"
  | "business"
  | "visitor_short_stay"
  | "ngo_organization"
  | "foreigner_international"
  | "shared_occupancy"
  | "couple"
  | "other";

export type TenantProfileForm = {
  tenant_category: TenantCategory;
  tenant_subtype: string;
  institution_name: string;
  student_id: string;
  sponsor_or_guardian_name: string;
  employer_or_business_name: string;
  occupation: string;
  work_location: string;
  number_of_occupants: string;
  children_count: string;
  parking_required: string;
  funding_source: string;
  guarantor_name: string;
  additional_notes: string;
};

type TenantProfileFieldsProps<T extends TenantProfileForm> = {
  form: T;
  update: <K extends keyof T>(key: K, value: T[K]) => void;
};

export const tenantCategoryOptions: Array<[TenantCategory, string]> = [
  ["student", "Student"],
  ["worker", "Worker"],
  ["family", "Family"],
  ["business", "Business"],
  ["visitor_short_stay", "Visitor / Short Stay"],
  ["ngo_organization", "NGO / Organization"],
  ["foreigner_international", "Foreigner / International"],
  ["shared_occupancy", "Shared Occupancy"],
  ["couple", "Couple"],
  ["other", "Other"]
];

export const subtypeOptions = {
  student: [
    ["nul_student", "NUL Student"],
    ["limkokwing_student", "Limkokwing Student"],
    ["tvet_student", "TVET Student"],
    ["college_student", "College Student"],
    ["other_student", "Other Student"]
  ],
  worker: [
    ["employed", "Employed"],
    ["government_worker", "Government Worker"],
    ["private_company_worker", "Private Company Worker"],
    ["self_employed", "Self-employed"],
    ["remote_worker", "Remote worker"],
    ["other_worker", "Other Worker"]
  ],
  family: [
    ["small_family", "Small Family"],
    ["single_parent", "Single parent"],
    ["large_family", "Large Family"],
    ["other_family", "Other Family"]
  ],
  business: [
    ["office_staff", "Office Staff"],
    ["shop_workers", "Shop Workers"],
    ["construction_team", "Construction Team"],
    ["other_business", "Other Business"]
  ],
  visitor_short_stay: [
    ["daily", "Daily"],
    ["weekly", "Weekly"],
    ["monthly", "Monthly"]
  ],
  ngo_organization: [
    ["ngo_staff", "NGO Staff"],
    ["church_organization", "Church Organization"],
    ["project_team", "Project Team"],
    ["other_organization", "Other Organization"]
  ],
  foreigner_international: [
    ["international_student", "International Student"],
    ["international_worker", "International Worker"],
    ["visitor", "Visitor"],
    ["other_international", "Other International"]
  ],
  shared_occupancy: [
    ["2_people_sharing", "2 People Sharing"],
    ["3_people_sharing", "3 People Sharing"],
    ["group_sharing", "Group Sharing"]
  ],
  couple: [
    ["married_couple", "Married Couple"],
    ["partners", "Partners"],
    ["other_couple", "Other Couple"]
  ],
  other: [
    ["other", "Other"]
  ]
} satisfies Record<TenantCategory, string[][]>;

export function defaultSubtype(category: TenantCategory) {
  return subtypeOptions[category][0][0];
}

export function tenantTypeFromCategory(category: TenantCategory) {
  return category === "student" ? "student" : "non_student";
}

export function TenantProfileFields<T extends TenantProfileForm>({
  form,
  update
}: TenantProfileFieldsProps<T>) {
  function updateCategory(category: TenantCategory) {
    update("tenant_category", category as T["tenant_category"]);
    update("tenant_subtype", defaultSubtype(category) as T["tenant_subtype"]);
  }

  return (
    <div className="profile-fieldset">
      <div className="form-grid">
        <label>
          Tenant category
          <select value={form.tenant_category} onChange={(event) => updateCategory(event.target.value as TenantCategory)}>
            {tenantCategoryOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>

        <label>
          Category detail
          <select value={form.tenant_subtype} onChange={(event) => update("tenant_subtype", event.target.value as T["tenant_subtype"])}>
            {subtypeOptions[form.tenant_category].map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
      </div>

      {form.tenant_category === "student" ? (
        <>
          <div className="form-grid">
            <label>Institution name<input required value={form.institution_name} onChange={(event) => update("institution_name", event.target.value as T["institution_name"])} /></label>
            <label>Student ID optional<input value={form.student_id} onChange={(event) => update("student_id", event.target.value as T["student_id"])} /></label>
          </div>
          <label>Sponsor or guardian optional<input value={form.sponsor_or_guardian_name} onChange={(event) => update("sponsor_or_guardian_name", event.target.value as T["sponsor_or_guardian_name"])} /></label>
        </>
      ) : null}

      {form.tenant_category === "worker" ? (
        <>
          <div className="form-grid">
            <label>Employer or business<input value={form.employer_or_business_name} onChange={(event) => update("employer_or_business_name", event.target.value as T["employer_or_business_name"])} /></label>
            <label>Occupation<input required value={form.occupation} onChange={(event) => update("occupation", event.target.value as T["occupation"])} /></label>
          </div>
          <label>Work location<input value={form.work_location} onChange={(event) => update("work_location", event.target.value as T["work_location"])} /></label>
        </>
      ) : null}

      {form.tenant_category === "family" ? (
        <>
          <div className="form-grid">
            <label>Number of occupants<input required inputMode="numeric" value={form.number_of_occupants} onChange={(event) => update("number_of_occupants", event.target.value as T["number_of_occupants"])} /></label>
            <label>Children count<input inputMode="numeric" value={form.children_count} onChange={(event) => update("children_count", event.target.value as T["children_count"])} /></label>
          </div>
          <label>Parking required<select value={form.parking_required} onChange={(event) => update("parking_required", event.target.value as T["parking_required"])}>
            <option value="">No preference</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select></label>
        </>
      ) : null}

      {["business", "visitor_short_stay", "ngo_organization", "foreigner_international", "shared_occupancy", "couple", "other"].includes(form.tenant_category) ? (
        <>
          <div className="form-grid">
            <label>Funding source optional<input value={form.funding_source} onChange={(event) => update("funding_source", event.target.value as T["funding_source"])} /></label>
            <label>Guarantor name optional<input value={form.guarantor_name} onChange={(event) => update("guarantor_name", event.target.value as T["guarantor_name"])} /></label>
          </div>
          <label>Additional notes optional<textarea value={form.additional_notes} onChange={(event) => update("additional_notes", event.target.value as T["additional_notes"])} /></label>
        </>
      ) : null}
    </div>
  );
}
