import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Landlord, LandlordRequest, Listing, PropertyItem, Room, SubscriptionPlan, Tenant } from "../../types";

type ManualLandlordForm = {
  full_name: string;
  email: string;
  phone: string;
  address: string;
};

type DistrictManualLandlordForm = {
  full_name: string;
  email: string;
  phone: string;
  address: string;
  emergency_contact: string;
  emergency_phone: string;
  preferred_response_method: string;
  response_contact_value: string;
  national_id: string;
  notes: string;
  property_name: string;
  area_id: string;
  village_id: string;
  property_address: string;
  total_rooms: string;
  single_rooms: string;
  double_rooms: string;
  single_room_prefix: string;
  double_room_prefix: string;
  starting_room_number: string;
};

type District = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  rollout_stage: string;
  description: string | null;
  activated_at: string | null;
  created_at?: string;
  updated_at?: string | null;
};

type DistrictArea = {
  id: string;
  district_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  description: string | null;
  created_at?: string;
  updated_at?: string | null;
};

type DistrictVillage = {
  id: string;
  area_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  description: string | null;
  created_at?: string;
  updated_at?: string | null;
};

type AreaForm = {
  id: string;
  district_id: string;
  name: string;
  description: string;
  is_active: boolean;
};

type VillageForm = {
  id: string;
  area_id: string;
  name: string;
  description: string;
  is_active: boolean;
};

type DistrictAdmin = {
  id: string;
  username?: string | null;
  temporary_password?: string | null;
  full_name: string;
  email: string;
  phone?: string | null;
  role: "district_admin";
  is_active: boolean;
  district_id: string;
  district_name: string;
};

type DistrictAdminSubscriptionPermission = {
  id: string;
  district_admin_user_id: string;
  district_id: string;
  can_manage_subscriptions: boolean;
};

type DistrictAdminForm = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  district_id: string;
};

type DistrictView = "districts" | "add-area" | "areas";

export type AdminSection =
  | "onboarding"
  | "requests"
  | "risk"
  | "gateway"
  | "reminders"
  | "plans"
  | "landlords"
  | "districts"
  | "district-admins"
  | "manual-landlord";

const emptyManual: ManualLandlordForm = {
  full_name: "",
  email: "",
  phone: "",
  address: ""
};

const emptyPlan = {
  name: "",
  monthly_price: "0",
  min_rooms: "1",
  max_rooms: "",
  features: ""
};

const emptyAreaForm: AreaForm = {
  id: "",
  district_id: "",
  name: "",
  description: "",
  is_active: true
};

const emptyDistrictManualLandlord: DistrictManualLandlordForm = {
  full_name: "",
  email: "",
  phone: "",
  address: "",
  emergency_contact: "",
  emergency_phone: "",
  preferred_response_method: "email",
  response_contact_value: "",
  national_id: "",
  notes: "",
  property_name: "",
  area_id: "",
  village_id: "",
  property_address: "",
  total_rooms: "1",
  single_rooms: "1",
  double_rooms: "0",
  single_room_prefix: "A",
  double_room_prefix: "B",
  starting_room_number: "101"
};

const emptyVillageForm: VillageForm = {
  id: "",
  area_id: "",
  name: "",
  description: "",
  is_active: true
};

const emptyDistrictAdminForm: DistrictAdminForm = {
  id: "",
  full_name: "",
  email: "",
  phone: "",
  district_id: ""
};

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

async function loadOptional<T>(path: string, fallback: T): Promise<T> {
  try {
    return (await apiFetch(path)) as T;
  } catch (err) {
    console.warn(`Admin optional data failed for ${path}`, err);
    return fallback;
  }
}

export function AdminDashboardPage({ section = "onboarding" }: { section?: AdminSection }) {
  const { user } = useAuth();
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [requests, setRequests] = useState<LandlordRequest[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [riskCenter, setRiskCenter] = useState<any>(null);
  const [reminderLogs, setReminderLogs] = useState<any[]>([]);
  const [paymentHealth, setPaymentHealth] = useState<any>(null);
  const [districts, setDistricts] = useState<District[]>([]);
  const [areas, setAreas] = useState<DistrictArea[]>([]);
  const [villages, setVillages] = useState<DistrictVillage[]>([]);
  const [districtAdmins, setDistrictAdmins] = useState<DistrictAdmin[]>([]);
  const [subscriptionPermissions, setSubscriptionPermissions] = useState<DistrictAdminSubscriptionPermission[]>([]);

  const [manual, setManual] = useState<ManualLandlordForm>(emptyManual);
  const [districtManual, setDistrictManual] = useState<DistrictManualLandlordForm>(emptyDistrictManualLandlord);
  const [manualResult, setManualResult] = useState<any>(null);
  const [planForm, setPlanForm] = useState(emptyPlan);
  const [areaForm, setAreaForm] = useState<AreaForm>(emptyAreaForm);
  const [villageForm, setVillageForm] = useState<VillageForm>(emptyVillageForm);
  const [districtAdminForm, setDistrictAdminForm] = useState<DistrictAdminForm>(emptyDistrictAdminForm);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");
  const [districtView, setDistrictView] = useState<DistrictView>("districts");
  const [selectedDistrictId, setSelectedDistrictId] = useState("all");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const canLoadLandlordOperations = user?.role !== "national_admin";
      const [landlordItems, requestItems, districtItems, areaItems, districtAdminItems] = await Promise.all([
        canLoadLandlordOperations ? loadOptional<Landlord[]>("/landlords", []) : Promise.resolve([]),
        canLoadLandlordOperations ? loadOptional<LandlordRequest[]>("/landlords/requests", []) : Promise.resolve([]),
        loadOptional<District[]>("/districts", []),
        loadOptional<DistrictArea[]>("/district-areas", []),
        loadOptional<DistrictAdmin[]>("/admin/district-admins", [])
      ]);

      setLandlords(landlordItems);
      setRequests(requestItems);
      setDistricts(districtItems);
      setAreas(areaItems);
      setDistrictAdmins(districtAdminItems);
      setVillages(await loadOptional<DistrictVillage[]>("/district-areas/villages", []));

      if (!areaForm.district_id && districtItems.length > 0) {
        setAreaForm((current) => ({ ...current, district_id: districtItems[0].id }));
      }

      if (!villageForm.area_id && areaItems.length > 0) {
        setVillageForm((current) => ({ ...current, area_id: areaItems[0].id }));
      }

      if (!districtManual.area_id && areaItems.length > 0) {
        setDistrictManual((current) => ({ ...current, area_id: areaItems[0].id }));
      }

      if (!districtAdminForm.district_id && districtItems.length > 0) {
        setDistrictAdminForm((current) => ({ ...current, district_id: districtItems[0].id }));
      }

      const [listingItems, propertyItems, roomItems, tenantItems, planItems] = await Promise.all([
        loadOptional<Listing[]>("/listings/mine", []),
        canLoadLandlordOperations ? loadOptional<PropertyItem[]>("/properties", []) : Promise.resolve([]),
        canLoadLandlordOperations ? loadOptional<Room[]>("/rooms", []) : Promise.resolve([]),
        canLoadLandlordOperations ? loadOptional<Tenant[]>("/tenants", []) : Promise.resolve([]),
        loadOptional<SubscriptionPlan[]>("/subscriptions/plans", [])
      ]);

      setListings(listingItems);
      setProperties(propertyItems);
      setRooms(roomItems);
      setTenants(tenantItems);
      setPlans(planItems);
      setSubscriptionPermissions(
        await loadOptional<DistrictAdminSubscriptionPermission[]>("/subscriptions/district-permissions", [])
      );

      const [riskItems, reminderItems, healthItems] = await Promise.all([
        loadOptional<any>("/admin/ai-risk-center", null),
        loadOptional<any[]>("/reminders/mine", []),
        loadOptional<any>("/payments/gateway-health", null)
      ]);

      setRiskCenter(riskItems);
      setReminderLogs(reminderItems);
      setPaymentHealth(healthItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load admin data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [user?.role]);

  function updateManual<K extends keyof ManualLandlordForm>(key: K, value: ManualLandlordForm[K]) {
    setManual((current) => ({ ...current, [key]: value }));
  }

  function updateDistrictManual<K extends keyof DistrictManualLandlordForm>(key: K, value: DistrictManualLandlordForm[K]) {
    setDistrictManual((current) => {
      if (key === "area_id") {
        return { ...current, [key]: value, village_id: "" };
      }
      return { ...current, [key]: value };
    });
  }

  function updateAreaForm<K extends keyof AreaForm>(key: K, value: AreaForm[K]) {
    setAreaForm((current) => ({ ...current, [key]: value }));
  }

  function updateVillageForm<K extends keyof VillageForm>(key: K, value: VillageForm[K]) {
    setVillageForm((current) => ({ ...current, [key]: value }));
  }

  function updateDistrictAdminForm<K extends keyof DistrictAdminForm>(key: K, value: DistrictAdminForm[K]) {
    setDistrictAdminForm((current) => ({ ...current, [key]: value }));
  }

  function editDistrictAdmin(admin: DistrictAdmin) {
    setDistrictAdminForm({
      id: admin.id,
      full_name: admin.full_name,
      email: admin.email,
      phone: admin.phone ?? "",
      district_id: admin.district_id
    });
    setSelectedDistrictId(admin.district_id);
  }

  async function saveDistrictAdmin(event: FormEvent) {
    event.preventDefault();
    setBusyId("district-admin");
    setNotice("");

    try {
      if (districtAdminForm.id) {
        const updatedAdmin = (await apiFetch(`/admin/district-admins/${districtAdminForm.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            full_name: districtAdminForm.full_name,
            email: districtAdminForm.email,
            phone: nullable(districtAdminForm.phone),
            district_id: districtAdminForm.district_id
          })
        })) as DistrictAdmin;

        setDistrictAdmins((current) => current.map((item) => (item.id === updatedAdmin.id ? updatedAdmin : item)));
        setNotice("District admin updated.");
      } else {
        const createdAdmin = (await apiFetch("/admin/district-admins", {
          method: "POST",
          body: JSON.stringify({
            full_name: districtAdminForm.full_name,
            email: districtAdminForm.email,
            phone: nullable(districtAdminForm.phone),
            district_id: districtAdminForm.district_id
          })
        })) as DistrictAdmin;

        setDistrictAdmins((current) => [...current, createdAdmin]);
        setNotice(
          createdAdmin.temporary_password
            ? `District admin account generated. Username: ${createdAdmin.username ?? "created"}, password: ${createdAdmin.temporary_password}`
            : `District admin account generated. Username: ${createdAdmin.username ?? "created"}`
        );
      }

      setDistrictAdminForm({
        ...emptyDistrictAdminForm,
        district_id: districtAdminForm.district_id
      });
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save district admin");
    } finally {
      setBusyId("");
    }
  }

  async function toggleDistrictAdmin(admin: DistrictAdmin) {
    setBusyId(admin.id);
    setNotice("");

    try {
      await apiFetch(`/admin/district-admins/${admin.id}/${admin.is_active ? "disable" : "enable"}`, {
        method: "POST"
      });
      setDistrictAdmins((current) => current.map((item) => item.id === admin.id ? { ...item, is_active: !admin.is_active } : item));
      setNotice(`${admin.full_name} is now ${admin.is_active ? "disabled" : "active"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update district admin");
    } finally {
      setBusyId("");
    }
  }

  async function toggleSubscriptionPermission(admin: DistrictAdmin) {
    const currentPermission = subscriptionPermissions.find(
      (permission) =>
        permission.district_admin_user_id === admin.id &&
        permission.district_id === admin.district_id
    );
    const nextValue = !currentPermission?.can_manage_subscriptions;

    setBusyId(`subscription-permission-${admin.id}`);
    setNotice("");

    try {
      await apiFetch("/subscriptions/district-permissions", {
        method: "POST",
        body: JSON.stringify({
          district_admin_user_id: admin.id,
          can_manage_subscriptions: nextValue
        })
      });

      setSubscriptionPermissions(
        await loadOptional<DistrictAdminSubscriptionPermission[]>("/subscriptions/district-permissions", [])
      );
      setNotice(
        `${admin.full_name} subscription pricing permission is now ${nextValue ? "Activated" : "Locked"}.`
      );
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update subscription permission");
    } finally {
      setBusyId("");
    }
  }

  async function deleteDistrictAdmin(admin: DistrictAdmin) {
    const confirmed = window.confirm(`Delete district admin ${admin.full_name}? This removes their district admin account.`);

    if (!confirmed) {
      return;
    }

    setBusyId(admin.id);
    setNotice("");

    try {
      await apiFetch(`/admin/district-admins/${admin.id}`, { method: "DELETE" });
      setDistrictAdmins((current) => current.filter((item) => item.id !== admin.id));
      setNotice("District admin deleted.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not delete district admin");
    } finally {
      setBusyId("");
    }
  }

  async function toggleDistrict(district: District) {
    setBusyId(district.id);
    setNotice("");

    try {
      const updatedDistrict = (await apiFetch(`/districts/${district.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: !district.is_active,
          description: district.is_active ? "Future rollout" : "Activated by admin"
        })
      })) as District;

      setDistricts((current) => current.map((item) => (item.id === updatedDistrict.id ? updatedDistrict : item)));
      setNotice(`${updatedDistrict.name} is now ${updatedDistrict.is_active ? "active" : "locked"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update district status");
    } finally {
      setBusyId("");
    }
  }

  async function submitArea(event: FormEvent) {
    event.preventDefault();
    setBusyId("add-area");
    setNotice("");

    try {
      const savedArea = (await apiFetch(areaForm.id ? `/district-areas/${areaForm.id}` : "/district-areas", {
        method: areaForm.id ? "PATCH" : "POST",
        body: JSON.stringify({
          district_id: areaForm.district_id,
          name: areaForm.name,
          description: nullable(areaForm.description),
          is_active: areaForm.is_active
        })
      })) as DistrictArea;

      setAreas((current) => areaForm.id ? current.map((item) => (item.id === savedArea.id ? savedArea : item)) : [...current, savedArea]);
      setAreaForm((current) => ({ ...emptyAreaForm, district_id: current.district_id }));
      if (!villageForm.area_id) {
        setVillageForm((current) => ({ ...current, area_id: savedArea.id }));
      }
      setDistrictView("areas");
      setNotice(`${savedArea.name} ${areaForm.id ? "updated" : "added"} successfully.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save area or village");
    } finally {
      setBusyId("");
    }
  }

  function editArea(area: DistrictArea) {
    setAreaForm({
      id: area.id,
      district_id: area.district_id,
      name: area.name,
      description: area.description ?? "",
      is_active: area.is_active
    });
    setDistrictView("add-area");
  }

  async function submitVillage(event: FormEvent) {
    event.preventDefault();
    setBusyId("add-village");
    setNotice("");

    try {
      const savedVillage = (await apiFetch(
        villageForm.id ? `/district-areas/villages/${villageForm.id}` : `/district-areas/${villageForm.area_id}/villages`,
        {
          method: villageForm.id ? "PATCH" : "POST",
          body: JSON.stringify({
            name: villageForm.name,
            description: nullable(villageForm.description),
            is_active: villageForm.is_active
          })
        }
      )) as DistrictVillage;

      setVillages((current) =>
        villageForm.id
          ? current.map((item) => (item.id === savedVillage.id ? savedVillage : item))
          : [...current, savedVillage]
      );
      setVillageForm((current) => ({ ...emptyVillageForm, area_id: current.area_id }));
      setNotice(`${savedVillage.name} ${villageForm.id ? "updated" : "added"} successfully.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save village");
    } finally {
      setBusyId("");
    }
  }

  function editVillage(village: DistrictVillage) {
    setVillageForm({
      id: village.id,
      area_id: village.area_id,
      name: village.name,
      description: village.description ?? "",
      is_active: village.is_active
    });
    setDistrictView("areas");
  }

  async function deleteVillage(village: DistrictVillage) {
    if (!window.confirm(`Delete ${village.name}? This should only be used before real listings depend on it.`)) return;
    setBusyId(village.id);
    setNotice("");

    try {
      await apiFetch(`/district-areas/villages/${village.id}`, { method: "DELETE" });
      setVillages((current) => current.filter((item) => item.id !== village.id));
      setNotice(`${village.name} deleted.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not delete village");
    } finally {
      setBusyId("");
    }
  }

  async function toggleVillage(village: DistrictVillage) {
    setBusyId(village.id);
    setNotice("");

    try {
      const updatedVillage = (await apiFetch(`/district-areas/villages/${village.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: !village.is_active
        })
      })) as DistrictVillage;

      setVillages((current) => current.map((item) => (item.id === updatedVillage.id ? updatedVillage : item)));
      setNotice(`${updatedVillage.name} is now ${updatedVillage.is_active ? "active" : "locked"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update village");
    } finally {
      setBusyId("");
    }
  }

  async function deleteArea(area: DistrictArea) {
    if (!window.confirm(`Delete ${area.name}? This should only be used before real listings depend on it.`)) return;
    setBusyId(area.id);
    setNotice("");

    try {
      await apiFetch(`/district-areas/${area.id}`, { method: "DELETE" });
      setAreas((current) => current.filter((item) => item.id !== area.id));
      setNotice(`${area.name} deleted.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not delete area or village");
    } finally {
      setBusyId("");
    }
  }

  async function toggleArea(area: DistrictArea) {
    setBusyId(area.id);
    setNotice("");

    try {
      const updatedArea = (await apiFetch(`/district-areas/${area.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: !area.is_active
        })
      })) as DistrictArea;

      setAreas((current) => current.map((item) => (item.id === updatedArea.id ? updatedArea : item)));
      setNotice(`${updatedArea.name} is now ${updatedArea.is_active ? "active" : "locked"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update area");
    } finally {
      setBusyId("");
    }
  }

  async function submitManual(event: FormEvent) {
    event.preventDefault();
    setNotice("");

    try {
      const result = (await apiFetch("/landlords/manual", {
        method: "POST",
        body: JSON.stringify({
          business_name: manual.full_name,
          full_name: manual.full_name,
          email: manual.email,
          phone: nullable(manual.phone),
          address: nullable(manual.address),
          district_id: assignedDistrict?.id ?? null
        })
      })) as { temporary_password?: string | null; landlord?: Landlord | null };

      setManual(emptyManual);
      setNotice(
        `Landlord account generated.${
          result.temporary_password ? ` Password: ${result.temporary_password}` : ""
        }`
      );
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not create landlord");
    }
  }

  async function submitDistrictManualLandlord(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    setManualResult(null);
    setBusyId("manual-landlord");

    try {
      const result = await apiFetch("/landlords/manual-create", {
        method: "POST",
        body: JSON.stringify({
          full_name: districtManual.full_name,
          email: districtManual.email,
          phone: nullable(districtManual.phone),
          address: nullable(districtManual.address),
          emergency_contact: nullable(districtManual.emergency_contact),
          emergency_phone: nullable(districtManual.emergency_phone),
          preferred_response_method: districtManual.preferred_response_method,
          response_contact_value: nullable(districtManual.response_contact_value),
          national_id: nullable(districtManual.national_id),
          notes: nullable(districtManual.notes),
          property_name: districtManual.property_name,
          area_id: districtManual.area_id,
          village_id: districtManual.village_id,
          property_address: nullable(districtManual.property_address),
          total_rooms: Number(districtManual.total_rooms),
          single_rooms: Number(districtManual.single_rooms),
          double_rooms: Number(districtManual.double_rooms),
          single_room_prefix: districtManual.single_room_prefix,
          double_room_prefix: districtManual.double_room_prefix,
          starting_room_number: Number(districtManual.starting_room_number)
        })
      });

      setManualResult(result);
      setDistrictManual((current) => ({
        ...emptyDistrictManualLandlord,
        area_id: current.area_id,
        village_id: current.village_id
      }));
      setNotice("Landlord, property, and rooms created.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not manually add landlord");
    } finally {
      setBusyId("");
    }
  }

  async function decideRequest(request: LandlordRequest, action: "request-verification" | "reject") {
    setBusyId(request.id);
    setNotice("");

    try {
      const result = (await apiFetch(`/landlords/requests/${request.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({
          admin_note: action === "request-verification" ? "Verification information requested." : "Rejected by admin."
        })
      })) as { verification_url?: string | null };

      setNotice(
        action === "request-verification" && result.verification_url
          ? `Verification requested. Link: ${result.verification_url}`
          : action === "request-verification"
          ? "Verification requested."
          : "Request rejected."
      );

      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : `Could not ${action} request`);
    } finally {
      setBusyId("");
    }
  }

  async function disableLandlord(landlord: Landlord) {
    setBusyId(landlord.id);
    setNotice("");

    try {
      await apiFetch(`/landlords/${landlord.id}/disable`, { method: "POST" });
      setNotice("Landlord disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable landlord");
    } finally {
      setBusyId("");
    }
  }

  async function savePlan(event: FormEvent) {
    event.preventDefault();
    setNotice("");

    try {
      await apiFetch("/subscriptions/plans", {
        method: "POST",
        body: JSON.stringify({
          name: planForm.name,
          min_rooms: Number(planForm.min_rooms),
          monthly_price: Number(planForm.monthly_price),
          max_properties: 1,
          max_rooms: planForm.max_rooms ? Number(planForm.max_rooms) : null,
          features: nullable(planForm.features),
          is_active: true
        })
      });

      setPlanForm(emptyPlan);
      setNotice("Subscription plan added.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save subscription plan");
    }
  }

  async function disablePlan(plan: SubscriptionPlan) {
    setBusyId(plan.id);
    setNotice("");

    try {
      await apiFetch(`/subscriptions/plans/${plan.id}`, { method: "DELETE" });
      setNotice("Subscription plan disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable plan");
    } finally {
      setBusyId("");
    }
  }

  async function runReminders() {
    setBusyId("run-reminders");
    setNotice("");

    try {
      const result = (await apiFetch("/admin/run-reminders", { method: "POST" })) as {
        tenant_rent_reminders_generated: number;
        subscription_reminders_generated: number;
        skipped_duplicates: number;
      };

      setNotice(
        `Reminders generated: rent ${result.tenant_rent_reminders_generated}, subscriptions ${result.subscription_reminders_generated}, skipped duplicates ${result.skipped_duplicates}.`
      );

      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not run reminders");
    } finally {
      setBusyId("");
    }
  }

  const activeDistricts = districts.filter((district) => district.is_active).length;
  const lockedDistricts = districts.filter((district) => !district.is_active).length;
  const activeAreas = areas.filter((area) => area.is_active).length;
  const lockedAreas = areas.filter((area) => !area.is_active).length;
  const isDistrictAdmin = user?.role === "district_admin";
  const assignedDistrict = districts[0] ?? null;
  const effectiveDistrictId = isDistrictAdmin ? assignedDistrict?.id ?? "none" : selectedDistrictId;
  const districtScoped = isDistrictAdmin || effectiveDistrictId !== "all";
  const selectedDistrict = isDistrictAdmin ? assignedDistrict : districts.find((district) => district.id === effectiveDistrictId);
  const districtAreas = selectedDistrict ? areas.filter((area) => area.district_id === selectedDistrict.id) : [];
  const manageableAreas = isDistrictAdmin ? districtAreas : areas;
  const districtManualVillageOptions = villages.filter((village) => village.area_id === districtManual.area_id);
  const activeDistrictAreas = districtAreas.filter((area) => area.is_active);
  const activeDistrictRooms = rooms.filter((room) => room.status !== "maintenance");
  const verifiedDistrictProperties = properties.filter((property) => property.id);
  const filteredDistrictAdmins = districtAdmins.filter((admin) => !districtScoped || admin.district_id === effectiveDistrictId);
  const filteredRequests = requests.filter((request) => {
    if (!districtScoped) return true;
    if (request.district_id === effectiveDistrictId) return true;
    const requestProperties = (request as any).properties ?? [];
    return requestProperties.some((property: any) => property.district_id === effectiveDistrictId);
  });
  const filteredLandlords = landlords.filter((landlord) => {
    if (!districtScoped) return true;
    const districtName = selectedDistrict?.name?.toLowerCase() ?? "";
    const landlordText = `${landlord.business_name ?? ""} ${(landlord as any).name ?? ""} ${landlord.address ?? ""} ${(landlord as any).location_area ?? ""}`.toLowerCase();

    return (
      (landlord as any).district_id === effectiveDistrictId ||
      (landlord as any).primary_district_id === effectiveDistrictId ||
      (districtName === "maseru" && (landlordText.includes("maseru") || landlordText.includes("roma")))
    );
  });
  const showDistrictSelector = !isDistrictAdmin && section !== "districts" && section !== "gateway";
  const headerStat = section === "district-admins"
    ? {
        value: filteredDistrictAdmins.length,
        label: districtScoped ? "district admins" : "district admins"
      }
    : user?.role === "national_admin"
    ? {
        value: activeDistricts,
        label: "active districts"
      }
    : {
        value: districtScoped ? filteredLandlords.length : landlords.length,
        label: districtScoped ? "district landlords" : "landlords"
      };

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>{adminSectionTitle(section)}</h1>
          <p>{adminSectionDescription(section)}</p>
        </div>

        <div className="header-stat">
          <strong>{headerStat.value}</strong>
          <span>{headerStat.label}</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      {!loading && !error && showDistrictSelector ? (
        <section className="panel compact-panel district-scope-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">District scope</p>
              <h2>Choose District first</h2>
              <p>
                National Admin actions are filtered by district so district
                admins, areas, and rollout records remain clearly structured.
              </p>
            </div>
          </div>

          <label>
            Active working district
            <select value={selectedDistrictId} onChange={(event) => setSelectedDistrictId(event.target.value)}>
              <option value="all">All districts</option>
              {districts.map((district) => (
                <option key={district.id} value={district.id}>
                  {district.name} {district.is_active ? "" : "(locked)"}
                </option>
              ))}
            </select>
          </label>

          {districtScoped ? (
            <div className="data-state compact-state">
              Showing records for {selectedDistrict?.name ?? "selected district"} only.
            </div>
          ) : (
            <div className="data-state compact-state">
              Choose a district for operational work. Use all districts only for national overview checks.
            </div>
          )}
        </section>
      ) : null}

      {!loading && !error ? (
        <>
          {section === "onboarding" ? (
            <div className="admin-grid single-admin-grid">
              <form className="panel form-panel" onSubmit={submitManual}>
                <div>
                  <p className="eyebrow">Manual onboarding</p>
                  <h2>Add landlord</h2>
                </div>

                <label>
                  Full names
                  <input required value={manual.full_name} onChange={(event) => updateManual("full_name", event.target.value)} />
                </label>

                <div className="form-grid">
                  <label>
                    Email
                    <input required type="email" value={manual.email} onChange={(event) => updateManual("email", event.target.value)} />
                  </label>

                  <label>
                    Phone
                    <input value={manual.phone} onChange={(event) => updateManual("phone", event.target.value)} />
                  </label>
                </div>

                <label>
                  Address
                  <input value={manual.address} onChange={(event) => updateManual("address", event.target.value)} />
                </label>

                <button className="primary-button" type="submit">
                  Generate landlord account
                </button>
              </form>
            </div>
          ) : null}

          {section === "manual-landlord" ? (
            <div className="admin-grid single-admin-grid">
              <form className="panel form-panel" onSubmit={submitDistrictManualLandlord}>
                <div>
                  <p className="eyebrow">District Admin</p>
                  <h2>Add Landlord</h2>
                  <p>{selectedDistrict ? `Creating inside ${selectedDistrict.name} only.` : "No district assignment found. Contact National Admin."}</p>
                </div>

                <div className="form-grid">
                  <label>Full names<input required value={districtManual.full_name} onChange={(event) => updateDistrictManual("full_name", event.target.value)} /></label>
                  <label>Email<input required type="email" value={districtManual.email} onChange={(event) => updateDistrictManual("email", event.target.value)} /></label>
                </div>

                <div className="form-grid">
                  <label>Phone<input value={districtManual.phone} onChange={(event) => updateDistrictManual("phone", event.target.value)} /></label>
                  <label>National ID optional<input value={districtManual.national_id} onChange={(event) => updateDistrictManual("national_id", event.target.value)} /></label>
                </div>

                <label>Personal physical address<input value={districtManual.address} onChange={(event) => updateDistrictManual("address", event.target.value)} /></label>

                <div className="form-grid">
                  <label>Emergency contact<input value={districtManual.emergency_contact} onChange={(event) => updateDistrictManual("emergency_contact", event.target.value)} /></label>
                  <label>Emergency phone<input value={districtManual.emergency_phone} onChange={(event) => updateDistrictManual("emergency_phone", event.target.value)} /></label>
                </div>

                <div className="form-grid">
                  <label>
                    Preferred response method
                    <select value={districtManual.preferred_response_method} onChange={(event) => updateDistrictManual("preferred_response_method", event.target.value)}>
                      <option value="email">Email</option>
                      <option value="phone_call">Phone call</option>
                      <option value="sms">SMS</option>
                      <option value="whatsapp">WhatsApp</option>
                    </select>
                  </label>
                  <label>Response contact value<input value={districtManual.response_contact_value} onChange={(event) => updateDistrictManual("response_contact_value", event.target.value)} /></label>
                </div>

                <div>
                  <p className="eyebrow">Property/location</p>
                  <h2>Property and rooms</h2>
                </div>

                <label>Property name<input required value={districtManual.property_name} onChange={(event) => updateDistrictManual("property_name", event.target.value)} /></label>

                <div className="form-grid">
                  <label>
                    Area
                    <select required value={districtManual.area_id} onChange={(event) => updateDistrictManual("area_id", event.target.value)}>
                      <option value="">Choose area</option>
                      {manageableAreas.map((area) => (
                        <option key={area.id} value={area.id}>{area.name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Village/location
                    <select required value={districtManual.village_id} onChange={(event) => updateDistrictManual("village_id", event.target.value)}>
                      <option value="">Choose village</option>
                      {districtManualVillageOptions.map((village) => (
                        <option key={village.id} value={village.id}>{village.name}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <label>Property physical address<input value={districtManual.property_address} onChange={(event) => updateDistrictManual("property_address", event.target.value)} /></label>

                <div className="form-grid">
                  <label>Total rooms<input required type="number" min="1" value={districtManual.total_rooms} onChange={(event) => updateDistrictManual("total_rooms", event.target.value)} /></label>
                  <label>Single rooms<input required type="number" min="0" value={districtManual.single_rooms} onChange={(event) => updateDistrictManual("single_rooms", event.target.value)} /></label>
                  <label>Double rooms<input required type="number" min="0" value={districtManual.double_rooms} onChange={(event) => updateDistrictManual("double_rooms", event.target.value)} /></label>
                </div>

                <div className="form-grid">
                  <label>Single room prefix<input required value={districtManual.single_room_prefix} onChange={(event) => updateDistrictManual("single_room_prefix", event.target.value)} /></label>
                  <label>Double room prefix<input required value={districtManual.double_room_prefix} onChange={(event) => updateDistrictManual("double_room_prefix", event.target.value)} /></label>
                  <label>Starting room number<input required type="number" min="1" value={districtManual.starting_room_number} onChange={(event) => updateDistrictManual("starting_room_number", event.target.value)} /></label>
                </div>

                <label>Notes optional<textarea value={districtManual.notes} onChange={(event) => updateDistrictManual("notes", event.target.value)} /></label>

                <button className="primary-button" type="submit" disabled={busyId === "manual-landlord" || !selectedDistrict}>
                  {busyId === "manual-landlord" ? "Creating..." : "Generate account and rooms"}
                </button>
              </form>

              {manualResult ? (
                <section className="panel">
                  <p className="eyebrow">Created</p>
                  <h2>{manualResult.property_name}</h2>
                  <div className="metric-grid compact-metrics">
                    <Metric label="Rooms created" value={manualResult.rooms_created ?? 0} />
                  </div>
                  <div className="data-state compact-state">
                    Username: {manualResult.username}. Temporary password: {manualResult.temporary_password}. Contact: {manualResult.landlord_email}{manualResult.landlord_phone ? ` / ${manualResult.landlord_phone}` : ""}.
                  </div>
                </section>
              ) : null}
            </div>
          ) : null}

          {section === "requests" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Requests</p>
                  <h2>Landlord requests</h2>
                </div>
              </div>

              <div className="list-stack compact-list">
                {filteredRequests.length === 0 ? <div className="data-state">No landlord requests in this district scope.</div> : null}

                {filteredRequests.map((request) => (
                  <article className="application-card" key={request.id}>
                    <div>
                      <div className="card-topline">
                        <StatusPill value={request.status} />
                        <span>{request.email}</span>
                      </div>

                      <strong>{request.full_name}</strong>
                      <p>
                        {request.phone ?? "No phone"}
                      </p>
                      <p>{request.message}</p>
                    </div>

                    <div className="review-actions">
                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "request-verification")}>
                        Request verification
                      </button>

                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "reject")}>
                        Reject
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "risk" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Decision support only</p>
                  <h2>AI Risk Center</h2>
                </div>
              </div>

              <div className="metric-grid compact-metrics">
                <Metric label="Pending requests" value={riskCenter?.daily_admin_summary?.new_landlord_requests ?? 0} />
                <Metric label="Public listings" value={riskCenter?.daily_admin_summary?.pending_listing_verification ?? 0} />
                <Metric label="Complaints" value={riskCenter?.daily_admin_summary?.unresolved_complaints ?? 0} />
                <Metric label="Payment alerts" value={riskCenter?.suspicious_payment_alerts?.length ?? 0} />
              </div>

              <div className="list-stack compact-list">
                {(riskCenter?.landlord_risk_cards ?? []).slice(0, 8).map((card: any) => (
                  <article className="row-item" key={card.landlord_id}>
                    <div>
                      <strong>{card.name ?? "Landlord"}</strong>
                      <p>
                        {card.system_landlord_number ?? "No landlord number"} - score {card.score}
                      </p>
                    </div>

                    <StatusPill value={card.level} />
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "gateway" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">MoPay readiness</p>
                  <h2>Payment gateway health</h2>
                </div>

                <StatusPill value={paymentHealth?.mopay_environment ?? "sandbox"} />
              </div>

              <div className="detail-grid compact">
                <div>
                  <span>Webhook URL</span>
                  <strong>{paymentHealth?.webhook_url ?? "Not set"}</strong>
                </div>

                <div>
                  <span>Callback URL</span>
                  <strong>{paymentHealth?.callback_url ?? "Not set"}</strong>
                </div>

                <div>
                  <span>Last webhook</span>
                  <strong>{paymentHealth?.last_webhook_received ? new Date(paymentHealth.last_webhook_received).toLocaleString() : "None yet"}</strong>
                </div>

                <div>
                  <span>Successful payments</span>
                  <strong>{paymentHealth?.successful_payment_count ?? 0}</strong>
                </div>

                <div>
                  <span>Failed webhooks</span>
                  <strong>{paymentHealth?.failed_webhook_count ?? 0}</strong>
                </div>
              </div>

              <div className="list-stack compact-list">
                {Object.entries(paymentHealth?.configured ?? {}).map(([key, value]) => (
                  <article className="row-item" key={key}>
                    <strong>{key}</strong>
                    <StatusPill value={value ? "configured" : "missing"} />
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "reminders" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Automation scaffold</p>
                  <h2>Payment reminders</h2>
                </div>

                {user?.role === "national_admin" ? (
                  <button type="button" disabled={busyId === "run-reminders"} onClick={runReminders}>
                    Run reminders
                  </button>
                ) : null}
              </div>

              <div className="data-state compact-state">
                Reminders are automated from actual rent due dates set by landlords and subscription renewal dates managed by district operations.
              </div>

              <div className="list-stack compact-list">
                {reminderLogs.length === 0 ? <div className="data-state">No reminder logs yet.</div> : null}

                {reminderLogs.slice(0, 20).map((log) => (
                  <article className="row-item" key={log.id}>
                    <div>
                      <strong>{String(log.reminder_type).replaceAll("_", " ")}</strong>
                      <p>{log.message}</p>
                    </div>

                    <StatusPill value={log.status} />
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "plans" ? (
            <form className="panel form-panel" onSubmit={savePlan}>
              <div>
                <p className="eyebrow">SaaS monetization</p>
                <h2>Add subscription plan</h2>
              </div>

              <label>
                Plan name
                <input required value={planForm.name} onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))} />
              </label>

              <div className="form-grid">
                <label>
                  Monthly price
                  <input required inputMode="numeric" value={planForm.monthly_price} onChange={(event) => setPlanForm((current) => ({ ...current, monthly_price: event.target.value }))} />
                </label>

                <label>
                  Min rooms
                  <input required inputMode="numeric" value={planForm.min_rooms} onChange={(event) => setPlanForm((current) => ({ ...current, min_rooms: event.target.value }))} />
                </label>
              </div>

              <label>
                Max rooms optional
                <input inputMode="numeric" value={planForm.max_rooms} onChange={(event) => setPlanForm((current) => ({ ...current, max_rooms: event.target.value }))} placeholder="Leave blank for no limit" />
              </label>

              <label>
                Features
                <textarea value={planForm.features} onChange={(event) => setPlanForm((current) => ({ ...current, features: event.target.value }))} />
              </label>

              <button className="primary-button" type="submit">
                Create plan
              </button>

              <div className="list-stack compact-list">
                {plans.map((plan) => (
                  <article className="row-item" key={plan.id}>
                    <div>
                      <strong>{plan.name}</strong>
                      <p>
                        M{Number(plan.monthly_price).toLocaleString()} monthly - {plan.min_rooms ?? 1} to {plan.max_rooms ?? "unlimited"} rooms
                      </p>
                    </div>

                    <button type="button" disabled={busyId === plan.id || !plan.is_active} onClick={() => disablePlan(plan)}>
                      {plan.is_active ? "Disable" : "Disabled"}
                    </button>
                  </article>
                ))}
              </div>
            </form>
          ) : null}

          {section === "districts" ? (
            isDistrictAdmin ? (
              <div className="panel">
                {!assignedDistrict ? (
                  <div className="data-state">No district assignment found. Contact National Admin.</div>
                ) : (
                  <>
                    <div className="section-heading">
                      <div>
                        <p className="eyebrow">{assignedDistrict.name} District Admin</p>
                        <h2>My District: {assignedDistrict.name}</h2>
                        <p>{assignedDistrict.description ?? "District operations for your assigned scope only."}</p>
                      </div>
                      <StatusPill value={assignedDistrict.is_active ? "active" : "locked"} />
                    </div>

                    <div className="metric-grid compact-metrics">
                      <Metric label="Active areas" value={activeDistrictAreas.length} />
                      <Metric label="District landlords" value={landlords.length} />
                      <Metric label="Pending landlord requests" value={requests.filter((request) => request.status === "pending").length} />
                      <Metric label="Verified properties" value={verifiedDistrictProperties.length} />
                      <Metric label="Active rooms" value={activeDistrictRooms.length} />
                      <Metric label="District tenants" value={tenants.length} />
                    </div>

                    <div className="list-stack compact-list">
                      <article className="row-item rich">
                        <div>
                          <div className="card-topline">
                            <StatusPill value={assignedDistrict.is_active ? "active" : "locked"} />
                            <span>{districtAreas.length} areas / villages</span>
                          </div>
                          <strong>{assignedDistrict.name}</strong>
                          <div className="amenities compact">
                            {districtAreas.length === 0 ? <span>No areas yet</span> : null}
                            {districtAreas.map((area) => (
                              <span className="area-admin-chip" key={area.id}>
                                <strong>{area.name}</strong>
                                <StatusPill value={area.is_active ? "active" : "locked"} />
                              </span>
                            ))}
                          </div>
                        </div>
                      </article>
                    </div>
                  </>
                )}
              </div>
            ) : (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">National rollout</p>
                  <h2>District access control</h2>
                </div>
              </div>

              <div className="amenities compact admin-subnav">
                <button
                  type="button"
                  className={`chip-button ${districtView === "districts" ? "active" : ""}`}
                  onClick={() => setDistrictView("districts")}
                >
                  Districts
                </button>

                <button
                  type="button"
                  className={`chip-button ${districtView === "add-area" ? "active" : ""}`}
                  onClick={() => setDistrictView("add-area")}
                >
                  Add Area
                </button>

                <button
                  type="button"
                  className={`chip-button ${districtView === "areas" ? "active" : ""}`}
                  onClick={() => setDistrictView("areas")}
                >
                  Areas
                </button>
              </div>

              {districtView === "districts" ? (
                <>
                  <p>
                    {isDistrictAdmin
                      ? "Manage rollout visibility for your assigned district only."
                      : "Rentalink is currently available in Roma village under Maseru district. District Admins can activate or lock areas and villages as rollout expands."}
                  </p>

                  <div className="metric-grid compact-metrics">
                    {isDistrictAdmin ? (
                      <>
                        <Metric label="Assigned districts" value={districts.length} />
                        <Metric label="Active areas" value={activeDistrictAreas.length} />
                        <Metric label="Locked areas" value={districtAreas.length - activeDistrictAreas.length} />
                      </>
                    ) : (
                      <>
                        <Metric label="Active districts" value={activeDistricts} />
                        <Metric label="Locked districts" value={lockedDistricts} />
                        <Metric label="Active areas" value={activeAreas} />
                        <Metric label="Locked areas" value={lockedAreas} />
                      </>
                    )}
                  </div>

                  <div className="list-stack compact-list">
                    {districts.map((district) => (
                      <article className="row-item rich" key={district.id}>
                        <div>
                          <div className="card-topline">
                            <StatusPill value={district.is_active ? "active" : "locked"} />
                          </div>

                          <strong>{district.name}</strong>
                          <p>{district.description ?? (district.is_active ? "Activated by admin" : "Future rollout")}</p>
                        </div>

                        <div className="review-actions">
                          <button type="button" className={`status-toggle ${district.is_active ? "active" : "locked"}`} disabled={busyId === district.id} onClick={() => toggleDistrict(district)}>
                            {district.is_active ? "Active" : "Locked"}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              ) : null}

              {districtView === "add-area" ? (
                <form className="panel form-panel" onSubmit={submitArea}>
                  <div>
                    <p className="eyebrow">District areas</p>
                  <h2>{areaForm.id ? "Edit area or village" : "Add area or village"}</h2>
                  </div>

                  <label>
                    Choose District
                    {isDistrictAdmin ? (
                      <input value={selectedDistrict?.name ?? "No district assignment found"} readOnly />
                    ) : (
                      <select required value={areaForm.district_id} onChange={(event) => updateAreaForm("district_id", event.target.value)}>
                        {districts.map((district) => (
                          <option key={district.id} value={district.id}>
                            {district.name}
                          </option>
                        ))}
                      </select>
                    )}
                  </label>

                  <label>
                    Area / village name
                    <input required placeholder="Example: Roma, Ha-Matala, Lithabaneng" value={areaForm.name} onChange={(event) => updateAreaForm("name", event.target.value)} />
                  </label>

                  <label>
                    Description
                    <textarea placeholder="Optional area description" value={areaForm.description} onChange={(event) => updateAreaForm("description", event.target.value)} />
                  </label>

                  <label>
                    Status
                    <select value={areaForm.is_active ? "active" : "locked"} onChange={(event) => updateAreaForm("is_active", event.target.value === "active")}>
                      <option value="active">Active</option>
                      <option value="locked">Locked</option>
                    </select>
                  </label>

                  <button className="primary-button" type="submit" disabled={busyId === "add-area"}>
                    {busyId === "add-area" ? "Saving..." : areaForm.id ? "Save area / village" : "Add area / village"}
                  </button>

                  {areaForm.id ? (
                    <button
                      type="button"
                      onClick={() => setAreaForm((current) => ({ ...emptyAreaForm, district_id: current.district_id }))}
                    >
                      Cancel edit
                    </button>
                  ) : null}
                </form>
              ) : null}

              {districtView === "areas" ? (
                <>
                  <form className="panel form-panel" onSubmit={submitVillage}>
                    <div>
                      <p className="eyebrow">District villages</p>
                      <h2>{villageForm.id ? "Edit village" : "Add village"}</h2>
                    </div>

                    <label>
                      Area
                      <select required value={villageForm.area_id} onChange={(event) => updateVillageForm("area_id", event.target.value)}>
                        {manageableAreas.map((area) => (
                          <option key={area.id} value={area.id}>
                            {area.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Village / location name
                      <input required placeholder="Example: Ha-Ntja" value={villageForm.name} onChange={(event) => updateVillageForm("name", event.target.value)} />
                    </label>

                    <label>
                      Description
                      <textarea placeholder="Optional village description" value={villageForm.description} onChange={(event) => updateVillageForm("description", event.target.value)} />
                    </label>

                    <label>
                      Status
                      <select value={villageForm.is_active ? "active" : "locked"} onChange={(event) => updateVillageForm("is_active", event.target.value === "active")}>
                        <option value="active">Active</option>
                        <option value="locked">Locked</option>
                      </select>
                    </label>

                    <div className="review-actions">
                      <button className="primary-button" type="submit" disabled={busyId === "add-village" || !villageForm.area_id}>
                        {busyId === "add-village" ? "Saving..." : villageForm.id ? "Save village" : "Add village"}
                      </button>
                      {villageForm.id ? (
                        <button type="button" onClick={() => setVillageForm((current) => ({ ...emptyVillageForm, area_id: current.area_id }))}>
                          Cancel edit
                        </button>
                      ) : null}
                    </div>
                  </form>

                  <div className="list-stack compact-list">
                    {districts.map((district) => {
                      const districtAreas = areas.filter((area) => area.district_id === district.id);

                      return (
                        <article className="row-item rich" key={district.id}>
                          <div>
                            <div className="card-topline">
                              <StatusPill value={district.is_active ? "active" : "locked"} />
                              <span>{districtAreas.length} areas</span>
                            </div>

                            <strong>{district.name}</strong>

                            <div className="list-stack compact-list">
                              {districtAreas.length === 0 ? <div className="data-state">No areas yet</div> : null}

                              {districtAreas.map((area) => {
                                const areaVillages = villages.filter((village) => village.area_id === area.id);

                                return (
                                  <div className="data-state compact-state" key={area.id}>
                                    <div className="section-heading">
                                      <div>
                                        <strong>{area.name}</strong>
                                        <p>{areaVillages.length} villages / locations</p>
                                      </div>
                                      <div className="review-actions">
                                        <button
                                          type="button"
                                          className={`status-toggle ${area.is_active ? "active" : "locked"}`}
                                          disabled={busyId === area.id}
                                          onClick={() => toggleArea(area)}
                                        >
                                          {area.is_active ? "Active" : "Locked"}
                                        </button>
                                        <button type="button" onClick={() => editArea(area)}>
                                          Edit Area
                                        </button>
                                      </div>
                                    </div>

                                    <div className="amenities compact">
                                      {areaVillages.length === 0 ? <span>No villages yet</span> : null}
                                      {areaVillages.map((village) => (
                                        <span className="area-admin-chip" key={village.id}>
                                          <strong>{village.name}</strong>
                                          <button
                                            type="button"
                                            className={`status-toggle ${village.is_active ? "active" : "locked"}`}
                                            disabled={busyId === village.id}
                                            onClick={() => toggleVillage(village)}
                                          >
                                            {village.is_active ? "Active" : "Locked"}
                                          </button>
                                          <button type="button" onClick={() => editVillage(village)}>
                                            Edit
                                          </button>
                                          <button type="button" disabled={busyId === village.id} onClick={() => deleteVillage(village)}>
                                            Delete
                                          </button>
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </>
              ) : null}

              <div className="data-state">
                Districts and areas are backed by the production database. Only the selected district management view is shown here.
              </div>
            </div>
            )
          ) : null}

          {section === "district-admins" ? (
            <div className="admin-grid">
              <form className="panel form-panel" onSubmit={saveDistrictAdmin}>
                <div>
                  <p className="eyebrow">District administration</p>
                  <h2>{districtAdminForm.id ? "Edit District Admin" : "Add District Admin"}</h2>
                  <p>Choose the district first, then create or update the admin responsible for that district.</p>
                </div>

                <label>
                  District
                  <select required value={districtAdminForm.district_id} onChange={(event) => updateDistrictAdminForm("district_id", event.target.value)}>
                    {districts.map((district) => (
                      <option key={district.id} value={district.id}>
                        {district.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Full name
                  <input required value={districtAdminForm.full_name} onChange={(event) => updateDistrictAdminForm("full_name", event.target.value)} />
                </label>

                <label>
                  Email
                  <input required type="email" value={districtAdminForm.email} onChange={(event) => updateDistrictAdminForm("email", event.target.value)} />
                </label>

                <label>
                  Phone
                  <input value={districtAdminForm.phone} onChange={(event) => updateDistrictAdminForm("phone", event.target.value)} />
                </label>

                <div className="review-actions">
                  <button className="primary-button" type="submit" disabled={busyId === "district-admin"}>
                    {districtAdminForm.id ? "Save District Admin" : "Generate Account"}
                  </button>

                  {districtAdminForm.id ? (
                    <button type="button" onClick={() => setDistrictAdminForm({ ...emptyDistrictAdminForm, district_id: selectedDistrictId === "all" ? districts[0]?.id ?? "" : selectedDistrictId })}>
                      Cancel edit
                    </button>
                  ) : null}
                </div>
              </form>

              <div className="panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">District Admins</p>
                    <h2>{districtScoped ? selectedDistrict?.name : "All districts"}</h2>
                  </div>
                </div>

                <div className="list-stack compact-list">
                  {filteredDistrictAdmins.length === 0 ? <div className="data-state">No district admins in this district scope.</div> : null}

                  {filteredDistrictAdmins.map((admin) => (
                    <article className="row-item rich" key={admin.id}>
                      <div>
                        <div className="card-topline">
                          <StatusPill value={admin.is_active ? "active" : "disabled"} />
                          <StatusPill
                            value={
                              subscriptionPermissions.some(
                                (permission) =>
                                  permission.district_admin_user_id === admin.id &&
                                  permission.district_id === admin.district_id &&
                                  permission.can_manage_subscriptions
                              )
                                ? "subscription activated"
                                : "subscription locked"
                            }
                          />
                          <span>{admin.username ?? "No identifier"}</span>
                        </div>

                        <strong>{admin.full_name}</strong>
                        <p>{admin.email} - {admin.phone ?? "No phone"}</p>
                        <small>{admin.district_name}</small>
                      </div>

                      <div className="review-actions">
                        <button type="button" onClick={() => editDistrictAdmin(admin)}>Edit</button>
                        <button type="button" disabled={busyId === admin.id} onClick={() => toggleDistrictAdmin(admin)}>
                          {admin.is_active ? "Disable" : "Enable"}
                        </button>
                        <button
                          type="button"
                          disabled={busyId === `subscription-permission-${admin.id}`}
                          onClick={() => toggleSubscriptionPermission(admin)}
                        >
                          {subscriptionPermissions.some(
                            (permission) =>
                              permission.district_admin_user_id === admin.id &&
                              permission.district_id === admin.district_id &&
                              permission.can_manage_subscriptions
                          )
                            ? "Lock subscription"
                            : "Activate subscription"}
                        </button>
                        <button type="button" disabled={busyId === admin.id} onClick={() => deleteDistrictAdmin(admin)}>
                          Delete
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {section === "landlords" ? (
            <div className="list-stack">
              {filteredLandlords.length === 0 ? <div className="data-state">No landlords in this district scope.</div> : null}

              {filteredLandlords.map((landlord) => (
                <article className="row-item rich" key={landlord.id}>
                  <div>
                    <div className="card-topline">
                      <StatusPill value={landlord.is_active ? "active" : "disabled"} />
                      <span>{landlord.system_landlord_number ?? "No system number"}</span>
                    </div>

                    <strong>{landlord.business_name ?? landlord.email}</strong>
                    <p>{landlord.address}</p>
                  </div>

                  <div className="review-actions">
                    <span>{landlord.contact_phone}</span>
                    <button type="button" disabled={busyId === landlord.id || !landlord.is_active} onClick={() => disableLandlord(landlord)}>
                      Disable
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function adminSectionTitle(section: AdminSection) {
  const titles: Record<AdminSection, string> = {
    onboarding: "Landlord onboarding",
    requests: "Landlord requests",
    risk: "AI Risk Center",
    gateway: "Payment gateway health",
    reminders: "Payment reminders",
    plans: "Subscription plans",
    landlords: "Landlords",
    "manual-landlord": "Add Landlord",
    districts: "Districts",
    "district-admins": "District Admins"
  };

  return titles[section];
}

function adminSectionDescription(section: AdminSection) {
  const descriptions: Record<AdminSection, string> = {
    onboarding: "Create landlord accounts manually and issue temporary credentials.",
    requests: "Approve or reject landlord applications submitted from the public request form.",
    risk: "Review automated risk signals, suspicious activity, and admin decision-support indicators.",
    gateway: "Monitor payment gateway readiness, webhook status, and missing production configuration.",
    reminders: "Generate and review automated rent and subscription reminder logs.",
    plans: "Create and manage SaaS subscription plans for landlords.",
    landlords: "View active landlords and disable accounts when necessary.",
    "manual-landlord": "Create an offline landlord account, property, and room inventory inside your assigned district.",
    districts: "Control districts, add areas, and manage rollout availability across Lesotho.",
    "district-admins": "Add, edit, disable, or delete District Admins after choosing their operating district."
  };

  return descriptions[section];
}
