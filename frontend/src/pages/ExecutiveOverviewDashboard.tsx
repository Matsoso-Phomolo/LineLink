import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import IntelligenceActivityFeed from "../components/IntelligenceActivityFeed";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function ExecutiveOverviewDashboard() {
  const [national, setNational] = useState<any>(null);
  const [districts, setDistricts] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOverview();
  }, []);

  async function loadOverview() {
    try {
      const [
        nationalRes,
        districtsRes,
        portfolioRes,
        tenantsRes,
        alertsRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/national-risk/summary`),
        fetch(`${API_BASE}/national-risk/high-risk-districts`),
        fetch(`${API_BASE}/portfolio-risk/summary`),
        fetch(`${API_BASE}/portfolio-risk/high-risk-tenants`),
        fetch(`${API_BASE}/portfolio-risk/overdue-clusters`),
      ]);

      setNational(await nationalRes.json());
      setDistricts(await districtsRes.json());
      setPortfolio(await portfolioRes.json());
      setTenants(await tenantsRes.json());
      setAlerts(await alertsRes.json());
    } catch (error) {
      console.error("Failed to load executive overview", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading Executive Overview...
      </div>
    );
  }

  const severeOverdue = alerts?.["30_plus_days"] || 0;

  const criticalTenants = tenants.filter(
    (tenant: any) => tenant.risk_level === "critical"
  );

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">
          Executive Overview
        </h1>

        <p className="text-gray-400 mt-2">
          Rentalink mission control for national, district, portfolio and tenant
          financial intelligence.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <Card
          title="National Risk Level"
          value={national?.national_risk_level || "stable"}
          color={riskTextColor(national?.national_risk_level)}
        />

        <Card
          title="National Collection Health"
          value={`${national?.national_collection_health || 0}%`}
          color="text-green-400"
        />

        <Card
          title="High Risk Districts"
          value={districts.length || 0}
          color="text-orange-400"
        />

        <Card
          title="Critical Tenants"
          value={criticalTenants.length || 0}
          color="text-red-400"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-10">
        <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-2xl font-semibold mb-6">
            National Snapshot
          </h2>

          <InfoRow
            label="Total Districts"
            value={national?.total_districts || 0}
          />

          <InfoRow
            label="Overdue Count"
            value={national?.overdue_count || 0}
            color="text-yellow-400"
          />

          <InfoRow
            label="National Overdue Exposure"
            value={`M${national?.national_overdue_exposure || 0}`}
            color="text-red-400"
          />

          <InfoRow
            label="High Risk Districts"
            value={districts.length}
            color="text-orange-400"
          />
        </section>

        <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-2xl font-semibold mb-6">
            Portfolio Snapshot
          </h2>

          <InfoRow
            label="Portfolio Risk Level"
            value={portfolio?.portfolio_risk_level || "stable"}
            color={riskTextColor(portfolio?.portfolio_risk_level)}
          />

          <InfoRow
            label="Total Tenants"
            value={portfolio?.total_tenants || 0}
          />

          <InfoRow
            label="30+ Days Overdue"
            value={severeOverdue}
            color="text-red-400"
          />

          <InfoRow
            label="High Risk Tenants"
            value={tenants.length}
            color="text-orange-400"
          />
        </section>
      </div>

      <section className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Intelligence Navigation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <QuickLink
            title="National Intelligence"
            description="Countrywide rental risk, collection health and district monitoring."
            to="/intelligence/national"
          />

          <QuickLink
            title="Portfolio Intelligence"
            description="Landlord portfolio risk, overdue clusters and tenant instability."
            to="/intelligence/portfolio"
          />

          <QuickLink
            title="Operational Alerts"
            description="SOC-style operational alerting for critical risk and overdue escalation."
            to="/intelligence/alerts"
          />

          <QuickLink
            title="Tenant Financial"
            description="Tenant payment scoring, financial behavior and receipt visibility."
            to="/intelligence/tenant"
          />
        </div>
      </section>

      <section className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Executive Priority Signals
        </h2>

        <div className="space-y-4">
          {national?.national_risk_level !== "stable" && (
            <Signal
              title="National risk deterioration"
              severity={national?.national_risk_level}
              description={`Current national risk level is ${national?.national_risk_level}.`}
            />
          )}

          {districts.length > 0 && (
            <Signal
              title="High-risk district exposure"
              severity="risky"
              description={`${districts.length} district(s) require monitoring.`}
            />
          )}

          {criticalTenants.length > 0 && (
            <Signal
              title="Critical tenant payment risk"
              severity="critical"
              description={`${criticalTenants.length} tenant(s) are classified as critical.`}
            />
          )}

          {severeOverdue > 0 && (
            <Signal
              title="Severe overdue exposure"
              severity="critical"
              description={`${severeOverdue} dues are overdue by 30+ days.`}
            />
          )}

          {national?.national_risk_level === "stable" &&
            districts.length === 0 &&
            criticalTenants.length === 0 &&
            severeOverdue === 0 && (
              <div className="bg-black border border-green-700 rounded-xl p-5">
                <p className="text-green-400 font-semibold">
                  No executive-level critical signals detected.
                </p>

                <p className="text-gray-400 mt-2">
                  Rentalink intelligence currently shows stable operational
                  conditions.
                </p>
              </div>
            )}
        </div>
      </section>

      <IntelligenceActivityFeed />
    </div>
  );
}

function Card({
  title,
  value,
  color,
}: {
  title: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <p className="text-gray-400 text-sm mb-2">{title}</p>

      <h2 className={`text-3xl font-bold ${color}`}>
        {value}
      </h2>
    </div>
  );
}

function InfoRow({
  label,
  value,
  color = "text-white",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-800 py-3">
      <span className="text-gray-400">{label}</span>

      <span className={`font-semibold ${color}`}>
        {value}
      </span>
    </div>
  );
}

function QuickLink({
  title,
  description,
  to,
}: {
  title: string;
  description: string;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="bg-black border border-gray-800 rounded-xl p-5 hover:border-cyan-700 transition block"
    >
      <h3 className="text-lg font-semibold text-cyan-400 mb-2">
        {title}
      </h3>

      <p className="text-gray-400 text-sm">
        {description}
      </p>
    </Link>
  );
}

function Signal({
  title,
  description,
  severity,
}: {
  title: string;
  description: string;
  severity: string;
}) {
  return (
    <div
      className={`bg-black rounded-xl p-5 border ${severityBorder(
        severity
      )}`}
    >
      <h3
        className={`font-semibold mb-2 ${riskTextColor(
          severity
        )}`}
      >
        {title}
      </h3>

      <p className="text-gray-400">
        {description}
      </p>
    </div>
  );
}

function riskTextColor(risk?: string) {
  if (risk === "critical") return "text-red-400";

  if (risk === "risky" || risk === "high")
    return "text-orange-400";

  if (risk === "watchlist" || risk === "medium")
    return "text-yellow-400";

  return "text-green-400";
}

function severityBorder(severity?: string) {
  if (severity === "critical")
    return "border-red-700";

  if (severity === "risky" || severity === "high")
    return "border-orange-700";

  if (severity === "watchlist" || severity === "medium")
    return "border-yellow-700";

  return "border-green-700";
}
