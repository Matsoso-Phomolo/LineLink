import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type IntelligenceLink = {
  label: string;
  to: string;
  roles: string[];
  end?: boolean;
};

const intelligenceLinks: IntelligenceLink[] = [
  {
    label: "Executive Overview",
    to: "/intelligence",
    roles: ["national_admin"],
    end: true,
  },
  {
    label: "National Intelligence",
    to: "/intelligence/national",
    roles: ["national_admin"],
  },
  {
    label: "District Intelligence",
    to: "/intelligence/district",
    roles: ["district_admin"],
  },
  {
    label: "Portfolio Intelligence",
    to: "/intelligence/portfolio",
    roles: ["landlord", "caretaker"],
  },
  {
    label: "Tenant Financial",
    to: "/intelligence/tenant",
    roles: ["tenant"],
  },
  {
    label: "Operational Alerts",
    to: "/intelligence/alerts",
    roles: ["national_admin", "district_admin", "landlord", "caretaker"],
  },
];

export default function IntelligenceLayout() {
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const visibleLinks = intelligenceLinks.filter((link) =>
    link.roles.includes(user?.role || "")
  );

  return (
    <div className="min-h-screen bg-black text-white flex">
      <aside className="w-72 bg-gray-950 border-r border-gray-800 p-6 hidden lg:block">
        <SidebarContent user={user} links={visibleLinks} />
      </aside>

      <main className="flex-1 min-w-0">
        <header className="bg-gray-950 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-cyan-400 font-semibold">
              AI-Enhanced Rental Governance
            </p>

            <h2 className="text-xl font-bold">
              Operational Intelligence Console
            </h2>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <span className="rounded-full bg-green-500/10 text-green-400 border border-green-700 px-3 py-1 text-sm">
              Live Intelligence
            </span>

            <span className="rounded-full bg-gray-900 text-gray-400 border border-gray-700 px-3 py-1 text-sm">
              Rentalink API
            </span>
          </div>

          <button
            type="button"
            className="lg:hidden rounded-xl border border-gray-700 bg-black px-4 py-2 text-sm text-cyan-300"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? "Close" : "Menu"}
          </button>
        </header>

        {mobileMenuOpen ? (
          <div className="lg:hidden border-b border-gray-800 bg-gray-950 px-4 py-4">
            <nav className="grid gap-2">
              {visibleLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end || link.to === "/intelligence"}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    [
                      "block rounded-xl px-4 py-3 text-sm font-medium transition",
                      isActive
                        ? "bg-cyan-500/15 text-cyan-300 border border-cyan-700"
                        : "text-gray-400 hover:bg-gray-900 hover:text-white border border-transparent",
                    ].join(" ")
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>

            <div className="mt-4 rounded-2xl border border-gray-800 bg-black p-4">
              <p className="text-xs uppercase tracking-widest text-gray-500">
                Signed in as
              </p>

              <p className="mt-2 font-semibold text-white">
                {user?.full_name || "Rentalink User"}
              </p>

              <p className="text-sm text-cyan-400">
                {user?.role || "unknown_role"}
              </p>
            </div>
          </div>
        ) : null}

        <section className="min-h-[calc(100vh-73px)]">
          <Outlet />
        </section>
      </main>
    </div>
  );
}

function SidebarContent({
  user,
  links,
}: {
  user: any;
  links: IntelligenceLink[];
}) {
  return (
    <>
      <div className="mb-10">
        <p className="text-cyan-400 text-sm font-semibold uppercase tracking-widest">
          Rentalink
        </p>

        <h1 className="text-2xl font-bold mt-2">
          Intelligence Center
        </h1>

        <p className="text-gray-500 text-sm mt-2">
          Governance, finance, risk and operational intelligence.
        </p>
      </div>

      <nav className="space-y-2">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end || link.to === "/intelligence"}
            className={({ isActive }) =>
              [
                "block rounded-xl px-4 py-3 text-sm font-medium transition",
                isActive
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-700"
                  : "text-gray-400 hover:bg-gray-900 hover:text-white border border-transparent",
              ].join(" ")
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-10 rounded-2xl border border-gray-800 bg-black p-4">
        <p className="text-xs uppercase tracking-widest text-gray-500">
          Signed in as
        </p>

        <p className="mt-2 font-semibold text-white">
          {user?.full_name || "Rentalink User"}
        </p>

        <p className="text-sm text-cyan-400">
          {user?.role || "unknown_role"}
        </p>
      </div>
    </>
  );
}
