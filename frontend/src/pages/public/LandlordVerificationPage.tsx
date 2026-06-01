import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../../api/client";

type PropertyForm = {
  property_name: string;
  district_id: string;
  area_id: string;
  village_location: string;
  address: string;
  description: string;
  total_rooms: string;
  single_rooms: string;
  double_rooms: string;
  single_room_prefix: string;
  double_room_prefix: string;
  starting_room_number: string;
  single_room_rent: string;
  double_room_rent: string;
};

type VerificationForm = {
  email: string;
  national_id: string;
  selfie_path: string;
  utility_bill_path: string;
  ownership_document_path: string;
  business_registration_path: string;
  additional_notes: string;
};

const emptyProperty = (): PropertyForm => ({
  property_name: "",
  district_id: "",
  area_id: "",
  village_location: "",
  address: "",
  description: "",
  total_rooms: "1",
  single_rooms: "1",
  double_rooms: "0",
  single_room_prefix: "A",
  double_room_prefix: "B",
  starting_room_number: "101",
  single_room_rent: "",
  double_room_rent: "",
});

const initialVerification: VerificationForm = {
  email: "",
  national_id: "",
  selfie_path: "",
  utility_bill_path: "",
  ownership_document_path: "",
  business_registration_path: "",
  additional_notes: "",
};

const romaVillageOptions = [
  "Hatabutle",
  "Mafikeng",
  "Thoteng",
  "Ten-House",
  "Liphehleng",
  "Liphakoeng",
  "Ha-Ntja",
  "Keiting",
  "Mangopeng",
];

type VerificationTokenRequest = {
  id: string;
  full_name: string;
  email: string;
  status: string;
};

type District = {
  id: string;
  name: string;
};

type DistrictArea = {
  id: string;
  district_id: string;
  name: string;
};

export function LandlordVerificationPage() {
  const { token } = useParams();
  const [requestId, setRequestId] = useState("");
  const [form, setForm] = useState(initialVerification);
  const [properties, setProperties] = useState<PropertyForm[]>([
    emptyProperty(),
  ]);
  const [districts, setDistricts] = useState<District[]>([]);
  const [areas, setAreas] = useState<DistrictArea[]>([]);
  const [tokenRequest, setTokenRequest] =
    useState<VerificationTokenRequest | null>(null);

  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loadingToken, setLoadingToken] = useState(Boolean(token));

  useEffect(() => {
    let ignore = false;

    Promise.all([
      apiFetch("/districts/active") as Promise<District[]>,
      apiFetch("/district-areas") as Promise<DistrictArea[]>,
    ])
      .then(([districtItems, areaItems]) => {
        if (ignore) return;
        setDistricts(districtItems);
        setAreas(areaItems);
        setProperties((current) =>
          current.map((property) => ({
            ...property,
            district_id: property.district_id || districtItems[0]?.id || "",
            area_id:
              property.area_id ||
              areaItems.find(
                (area) => area.district_id === (property.district_id || districtItems[0]?.id)
              )?.id ||
              "",
          }))
        );
      })
      .catch(() => {
        // Keep manual inputs usable if rollout metadata cannot load.
      });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!token) return;

    let ignore = false;
    setLoadingToken(true);
    setError("");

    apiFetch(`/landlords/requests/verification-token/${token}`)
      .then((request: VerificationTokenRequest) => {
        if (ignore) return;
        setTokenRequest(request);
        setRequestId(request.id);
        setForm((current) => ({ ...current, email: request.email }));
      })
      .catch((err) => {
        if (ignore) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to open verification link"
        );
      })
      .finally(() => {
        if (!ignore) setLoadingToken(false);
      });

    return () => {
      ignore = true;
    };
  }, [token]);

  function updateForm<K extends keyof VerificationForm>(
    key: K,
    value: VerificationForm[K]
  ) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateProperty<K extends keyof PropertyForm>(
    index: number,
    key: K,
    value: PropertyForm[K]
  ) {
    setProperties((current) =>
      current.map((property, currentIndex) =>
        currentIndex === index ? { ...property, [key]: value } : property
      )
    );
  }

  function updatePropertyDistrict(index: number, districtId: string) {
    const firstArea = areas.find((area) => area.district_id === districtId);
    setProperties((current) =>
      current.map((property, currentIndex) =>
        currentIndex === index
          ? {
              ...property,
              district_id: districtId,
              area_id: firstArea?.id || "",
            }
          : property
      )
    );
  }

  function addProperty() {
    setProperties((current) => [...current, emptyProperty()]);
  }

  function removeProperty(index: number) {
    setProperties((current) =>
      current.length === 1
        ? current
        : current.filter((_, currentIndex) => currentIndex !== index)
    );
  }

  function validateProperties() {
    for (const property of properties) {
      const total = Number(property.total_rooms);
      const singles = Number(property.single_rooms);
      const doubles = Number(property.double_rooms);

      if (singles + doubles !== total) {
        return `${
          property.property_name || "Property"
        } has invalid room totals. Single rooms + double rooms must equal total rooms.`;
      }

      if (
        property.single_room_prefix.trim().toLowerCase() ===
        property.double_room_prefix.trim().toLowerCase()
      ) {
        return `${
          property.property_name || "Property"
        } must use different prefixes for single and double rooms.`;
      }
    }

    return "";
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    setError("");
    setStatus("");

    const validationError = validateProperties();

    if (validationError) {
      setError(validationError);
      return;
    }

    if (!token && !requestId.trim()) {
      setError("Landlord request ID is required.");
      return;
    }

    setSubmitting(true);

    try {
      const endpoint = token
        ? `/landlords/requests/verification-token/${token}/submit`
        : `/landlords/requests/${requestId}/submit-verification`;

      await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({
          ...form,
          properties: properties.map((property) => ({
            property_name: property.property_name,
            district_id: property.district_id,
            area_id: property.area_id,
            village_location: property.village_location,
            address: property.address,
            description: property.description || null,
            total_rooms: Number(property.total_rooms),
            single_rooms: Number(property.single_rooms),
            double_rooms: Number(property.double_rooms),
            single_room_prefix: property.single_room_prefix,
            double_room_prefix: property.double_room_prefix,
            starting_room_number: Number(property.starting_room_number),
            single_room_rent: property.single_room_rent
              ? Number(property.single_room_rent)
              : null,
            double_room_rent: property.double_room_rent
              ? Number(property.double_room_rent)
              : null,
          })),
        }),
      });

      setForm(initialVerification);
      setProperties([emptyProperty()]);
      setStatus(
        "Verification submitted successfully. Rentalink administrators will review your information."
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to submit verification"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="center-page public-request-page">
      <section className="auth-shell public-request-shell">
        <div className="auth-copy">
          <div className="brand-mark light">
            <span>RL</span>
            <div>
              <strong>Rentalink</strong>
              <small>Verification</small>
            </div>
          </div>

          <div>
            <p className="eyebrow">Landlord verification</p>
            <h1>Submit your identity and property verification.</h1>
            <p>
              This form is used after the admin requests verification. Enter
              your identity documents and every property separately.
            </p>
          </div>

          <div className="privacy-note">
            Each property must have its own physical address, room totals,
            prefixes, starting room number, single rent, and double rent.
          </div>

          <a className="secondary-button" href="#/login">
            Back to sign in
          </a>
        </div>

        <form className="auth-card application-form-card" onSubmit={submit}>
          <div>
            <p className="eyebrow">Verification form</p>
            <h2>Identity details</h2>
          </div>

          {loadingToken ? (
            <div className="privacy-note">Opening secure verification link...</div>
          ) : tokenRequest ? (
            <div className="privacy-note">
              Secure link opened for <strong>{tokenRequest.full_name}</strong>{" "}
              using <strong>{tokenRequest.email}</strong>.
            </div>
          ) : (
            <label>
              Landlord request ID
              <input
                required={!token}
                value={requestId}
                onChange={(event) => setRequestId(event.target.value)}
                placeholder="Paste request ID from admin verification message"
              />
            </label>
          )}

          <label>
            Email used for landlord request
            <input
              required
              readOnly={Boolean(tokenRequest)}
              value={form.email}
              onChange={(event) => updateForm("email", event.target.value)}
              placeholder="landlord@example.com"
            />
          </label>

          <label>
            National ID
            <input
              required
              value={form.national_id}
              onChange={(event) =>
                updateForm("national_id", event.target.value)
              }
            />
          </label>

          <label>
            Selfie file path / URL
            <input
              value={form.selfie_path}
              onChange={(event) =>
                updateForm("selfie_path", event.target.value)
              }
              placeholder="Upload URL or stored file path"
            />
          </label>

          <label>
            Utility bill file path / URL
            <input
              value={form.utility_bill_path}
              onChange={(event) =>
                updateForm("utility_bill_path", event.target.value)
              }
            />
          </label>

          <label>
            Ownership document file path / URL
            <input
              value={form.ownership_document_path}
              onChange={(event) =>
                updateForm("ownership_document_path", event.target.value)
              }
            />
          </label>

          <label>
            Business registration file path / URL
            <input
              value={form.business_registration_path}
              onChange={(event) =>
                updateForm("business_registration_path", event.target.value)
              }
            />
          </label>

          <label>
            Additional notes
            <textarea
              value={form.additional_notes}
              onChange={(event) =>
                updateForm("additional_notes", event.target.value)
              }
              placeholder="Anything admin should know"
            />
          </label>

          <div className="section-heading">
            <div>
              <p className="eyebrow">Properties</p>
              <h2>Property details</h2>
            </div>

            <button type="button" onClick={addProperty}>
              Add property
            </button>
          </div>

          {properties.map((property, index) => (
            <section className="panel" key={index}>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Property {index + 1}</p>
                  <h3>{property.property_name || "New property"}</h3>
                </div>

                <button
                  type="button"
                  onClick={() => removeProperty(index)}
                  disabled={properties.length === 1}
                >
                  Remove
                </button>
              </div>

              <label>
                Property name
                <input
                  required
                  value={property.property_name}
                  onChange={(event) =>
                    updateProperty(index, "property_name", event.target.value)
                  }
                  placeholder="Matsoso Ten-House Holdings"
                />
              </label>

              <div className="form-grid">
                <label>
                  District
                  {districts.length > 0 ? (
                    <select
                      required
                      value={property.district_id}
                      onChange={(event) =>
                        updatePropertyDistrict(index, event.target.value)
                      }
                    >
                      <option value="">Choose district</option>
                      {districts.map((district) => (
                        <option key={district.id} value={district.id}>
                          {district.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      required
                      value={property.district_id}
                      onChange={(event) =>
                        updateProperty(index, "district_id", event.target.value)
                      }
                      placeholder="District UUID"
                    />
                  )}
                </label>

                <label>
                  Area
                  {areas.length > 0 ? (
                    <select
                      required
                      value={property.area_id}
                      onChange={(event) =>
                        updateProperty(index, "area_id", event.target.value)
                      }
                    >
                      <option value="">Choose area</option>
                      {areas
                        .filter((area) => area.district_id === property.district_id)
                        .map((area) => (
                          <option key={area.id} value={area.id}>
                            {area.name}
                          </option>
                        ))}
                    </select>
                  ) : (
                    <input
                    required
                    value={property.area_id}
                    onChange={(event) =>
                      updateProperty(index, "area_id", event.target.value)
                    }
                    placeholder="Area UUID"
                    />
                  )}
                </label>
              </div>

              <label>
                Area / village
                <input
                  required
                  value={property.village_location}
                  onChange={(event) =>
                    updateProperty(
                      index,
                      "village_location",
                      event.target.value
                    )
                  }
                  placeholder="Ten-House"
                />
              </label>

              <div className="chip-row" aria-label="Roma village shortcuts">
                {romaVillageOptions.map((village) => (
                  <button
                    key={village}
                    type="button"
                    className={
                      property.village_location === village
                        ? "chip active"
                        : "chip"
                    }
                    onClick={() =>
                      updateProperty(index, "village_location", village)
                    }
                  >
                    {village}
                  </button>
                ))}
              </div>

              <label>
                Property physical address
                <input
                  required
                  value={property.address}
                  onChange={(event) =>
                    updateProperty(index, "address", event.target.value)
                  }
                  placeholder="Full physical address"
                />
              </label>

              <label>
                Description
                <textarea
                  value={property.description}
                  onChange={(event) =>
                    updateProperty(index, "description", event.target.value)
                  }
                />
              </label>

              <div className="form-grid">
                <label>
                  Total rooms
                  <input
                    required
                    min="1"
                    type="number"
                    value={property.total_rooms}
                    onChange={(event) =>
                      updateProperty(index, "total_rooms", event.target.value)
                    }
                  />
                </label>

                <label>
                  Starting room number
                  <input
                    required
                    min="1"
                    type="number"
                    value={property.starting_room_number}
                    onChange={(event) =>
                      updateProperty(
                        index,
                        "starting_room_number",
                        event.target.value
                      )
                    }
                  />
                </label>
              </div>

              <div className="form-grid">
                <label>
                  Single rooms
                  <input
                    required
                    min="0"
                    type="number"
                    value={property.single_rooms}
                    onChange={(event) =>
                      updateProperty(index, "single_rooms", event.target.value)
                    }
                  />
                </label>

                <label>
                  Double rooms
                  <input
                    required
                    min="0"
                    type="number"
                    value={property.double_rooms}
                    onChange={(event) =>
                      updateProperty(index, "double_rooms", event.target.value)
                    }
                  />
                </label>
              </div>

              <div className="form-grid">
                <label>
                  Single prefix
                  <input
                    required
                    value={property.single_room_prefix}
                    onChange={(event) =>
                      updateProperty(
                        index,
                        "single_room_prefix",
                        event.target.value
                      )
                    }
                    placeholder="A"
                  />
                </label>

                <label>
                  Double prefix
                  <input
                    required
                    value={property.double_room_prefix}
                    onChange={(event) =>
                      updateProperty(
                        index,
                        "double_room_prefix",
                        event.target.value
                      )
                    }
                    placeholder="B"
                  />
                </label>
              </div>

              <div className="form-grid">
                <label>
                  Single room rent
                  <input
                    min="0"
                    type="number"
                    value={property.single_room_rent}
                    onChange={(event) =>
                      updateProperty(
                        index,
                        "single_room_rent",
                        event.target.value
                      )
                    }
                    placeholder="750"
                  />
                </label>

                <label>
                  Double room rent
                  <input
                    min="0"
                    type="number"
                    value={property.double_room_rent}
                    onChange={(event) =>
                      updateProperty(
                        index,
                        "double_room_rent",
                        event.target.value
                      )
                    }
                    placeholder="1200"
                  />
                </label>
              </div>
            </section>
          ))}

          {error ? <div className="form-error">{error}</div> : null}
          {status ? <div className="form-success">{status}</div> : null}

          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit verification"}
          </button>
        </form>
      </section>
    </main>
  );
}
